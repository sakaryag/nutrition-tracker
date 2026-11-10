(function () {
  'use strict';

  var COOKIE = 'nt_cam';
  var MAX_AGE = 400 * 24 * 60 * 60;

  function remembered() {
    var m = document.cookie.match(/(?:^|;\s*)nt_cam=([^;]*)/);
    var v = m ? decodeURIComponent(m[1]) : '';
    return v === 'granted' || v === 'denied' ? v : '';
  }

  function remember(result) {
    if (result !== 'granted' && result !== 'denied') return;
    if (remembered() === result) return;
    document.cookie = COOKIE + '=' + result + '; max-age=' + MAX_AGE + '; path=/; SameSite=Lax' +
      (location.protocol === 'https:' ? '; Secure' : '');
  }

  function state() {
    try {
      if (!navigator.permissions || !navigator.permissions.query) return Promise.resolve('unknown');
      return Promise.resolve(navigator.permissions.query({ name: 'camera' })).then(function (s) {
        var v = s && s.state;
        if (v === 'granted') remember('granted');
        return v === 'granted' || v === 'denied' || v === 'prompt' ? v : 'unknown';
      }, function () { return 'unknown'; });
    } catch (_) {
      return Promise.resolve('unknown');
    }
  }

  function forgetsGrant() {
    if (remembered() !== 'granted') return Promise.resolve(false);
    return state().then(function (s) { return s === 'prompt'; });
  }

  // True when we should not show a permission prompt (browser or our cookie says denied).
  function blocked() {
    return state().then(function (s) {
      return s === 'denied' || (remembered() === 'denied' && s !== 'granted');
    });
  }

  function getStream(constraints) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return Promise.reject(new Error('getUserMedia unsupported'));
    }
    return navigator.mediaDevices.getUserMedia(constraints).then(function (s) {
      remember('granted');
      return s;
    }, function (err) {
      var n = err && err.name;
      if (n === 'NotAllowedError' || n === 'SecurityError' || n === 'PermissionDeniedError') remember('denied');
      throw err;
    });
  }

  window.NTCamera = {
    state: state,
    remember: remember,
    remembered: remembered,
    forgetsGrant: forgetsGrant,
    blocked: blocked,
    getStream: getStream,
  };
})();
