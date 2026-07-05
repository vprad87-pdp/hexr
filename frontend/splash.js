/*
 * HexR intro splash — self-contained, zero dependencies.
 * Concept: a short "encoded" string resolves into a honeycomb of hexagons,
 * which then collapses into the ⬡ HexR logo before fading into the app.
 *
 * Integration: drop this file in /frontend and add ONE line to the <head> of
 * index.html (before app.js):
 *     <script src="/splash.js"></script>
 * It injects its own styles + overlay, plays on every page load, removes
 * itself when done, and respects prefers-reduced-motion.
 */
(function () {
  'use strict';

  var HOLD = 3200;   // ms the splash stays before it begins fading
  var CREDIT = 'Pradeep'; // sign-off shown under the logo (set '' to hide)
  // How often the splash plays: 'every' | 'session' (once per tab session) | 'device' (once ever) | 'never'
  var FREQ = 'session';
  var FADE = 520;  // ms fade-out duration
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ── honeycomb: 19 hexagons (axial cluster, radius 2) ──────────────────────
  function buildCells() {
    var cx = 140, cy = 140, R = 18, rr = R * 0.92;
    var verts = [];
    for (var k = 0; k < 6; k++) {
      var a = (Math.PI / 180) * (60 * k);
      verts.push([Math.cos(a), Math.sin(a)]);
    }
    var cells = [];
    for (var q = -2; q <= 2; q++) {
      for (var r = Math.max(-2, -q - 2); r <= Math.min(2, -q + 2); r++) {
        var x = cx + 1.5 * R * q;
        var y = cy + Math.sqrt(3) * R * (r + q / 2);
        var dist = (Math.abs(q) + Math.abs(r) + Math.abs(q + r)) / 2;
        var lit = ((((q * 3 + r * 5) % 7) + 7) % 7) < 3; // deterministic pattern
        var pts = verts.map(function (v) {
          return (x + rr * v[0]).toFixed(1) + ',' + (y + rr * v[1]).toFixed(1);
        }).join(' ');
        cells.push({
          points: pts,
          fill: lit ? '#c5cae9' : '#5c6bc0',
          delay: (0.6 + dist * 0.17).toFixed(2)
        });
      }
    }
    return cells;
  }

  var CSS = [
    '#hexr-splash{position:fixed;inset:0;z-index:9999;display:flex;align-items:center;justify-content:center;',
      'background:radial-gradient(circle at 50% 44%,#283593 0%,#1a237e 55%,#121858 100%);}',
    '#hexr-splash .hexr-stage{position:relative;width:300px;height:300px;display:flex;align-items:center;justify-content:center;}',
    '#hexr-splash .hexr-svg{position:absolute;overflow:visible;}',
    '#hexr-splash .hexr-code{position:absolute;opacity:0;font-family:ui-monospace,"SF Mono",Menlo,monospace;',
      'font-size:1.05rem;color:#9fa8da;white-space:nowrap;animation:hexr-textin .55s ease .1s both,hexr-textout .5s ease .9s forwards;}',
    '#hexr-splash .hexr-cell{transform-box:fill-box;transform-origin:center;opacity:0;animation:hexr-cellin .65s cubic-bezier(.34,.9,.4,1) forwards;}',
    '#hexr-splash .hexr-cluster{transform-origin:140px 140px;animation:hexr-clusterout .6s cubic-bezier(.7,0,.3,1) 1.95s forwards;}',
    '#hexr-splash .hexr-logo{position:absolute;text-align:center;opacity:0;animation:hexr-login .7s cubic-bezier(.2,.7,.3,1) 2.05s both;}',
    '#hexr-splash .hexr-mark{color:#fff;font-size:2.4rem;font-weight:700;letter-spacing:4px;}',
    '#hexr-splash .hexr-tag{color:#c5cae9;font-size:.85rem;letter-spacing:1px;margin-top:6px;}',
    '#hexr-splash .hexr-credit{position:absolute;bottom:-8px;text-align:center;opacity:0;color:#7986cb;',
      'font-size:.72rem;letter-spacing:3px;text-transform:uppercase;animation:hexr-signoff .6s ease 2.55s both;}',
    '#hexr-splash.hexr-exit{animation:hexr-splashout .5s ease forwards;pointer-events:none;}',
    '@keyframes hexr-textin{from{opacity:0;letter-spacing:1px;}to{opacity:.85;letter-spacing:6px;}}',
    '@keyframes hexr-textout{to{opacity:0;filter:blur(7px);transform:translateY(-10px);}}',
    '@keyframes hexr-cellin{from{opacity:0;transform:scale(.3);}to{opacity:1;transform:scale(1);}}',
    '@keyframes hexr-clusterout{to{opacity:0;transform:scale(.55);}}',
    '@keyframes hexr-login{0%{opacity:0;transform:scale(.82);}60%{opacity:1;}100%{opacity:1;transform:scale(1);}}',
    '@keyframes hexr-splashout{to{opacity:0;}}',
    '@keyframes hexr-signoff{from{opacity:0;transform:translateY(6px);}to{opacity:.7;transform:translateY(0);}}',
    /* reduced-motion: no build, just a gentle logo fade */
    '#hexr-splash.hexr-reduced .hexr-code,#hexr-splash.hexr-reduced .hexr-svg{display:none;}',
    '#hexr-splash.hexr-reduced .hexr-logo{animation:hexr-login .4s ease both;}'
  ].join('');

  function run() {
    if (document.getElementById('hexr-splash')) return;

    var style = document.createElement('style');
    style.id = 'hexr-splash-style';
    style.textContent = CSS;
    document.head.appendChild(style);

    var polys = reduce ? '' : buildCells().map(function (c) {
      return '<polygon class="hexr-cell" points="' + c.points + '" fill="' + c.fill +
             '" style="animation-delay:' + c.delay + 's"></polygon>';
    }).join('');

    var overlay = document.createElement('div');
    overlay.id = 'hexr-splash';
    if (reduce) overlay.className = 'hexr-reduced';
    overlay.innerHTML =
      '<div class="hexr-stage">' +
        '<div class="hexr-code">aGVsbG8gd29ybGQ</div>' +
        '<svg class="hexr-svg" viewBox="0 0 280 280" width="280" height="280"><g class="hexr-cluster">' + polys + '</g></svg>' +
        '<div class="hexr-logo"><div class="hexr-mark">\u2B21 HexR</div><div class="hexr-tag">Your personal hexagonal QR code</div></div>' +
        (CREDIT ? '<div class="hexr-credit">by ' + CREDIT + '</div>' : '') +
      '</div>';
    document.body.appendChild(overlay);

    var hold = reduce ? 700 : HOLD;
    setTimeout(function () {
      overlay.classList.add('hexr-exit');
      setTimeout(function () { if (overlay.parentNode) overlay.parentNode.removeChild(overlay); }, FADE);
    }, hold);
  }

  function shouldRun() {
    if (FREQ === 'never') return false;
    if (FREQ === 'every') return true;
    var store = FREQ === 'device' ? window.localStorage : window.sessionStorage;
    try {
      if (store.getItem('hexr-splash-seen') === '1') return false;
      store.setItem('hexr-splash-seen', '1');
    } catch (e) {}
    return true;
  }

  if (!shouldRun()) return;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
