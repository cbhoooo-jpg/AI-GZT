/* ==================================================================
   主题工具 ThemeKit
   启动时读取 /api/config/get 的 theme_primary_color 覆写 CSS 变量
   派生色（hover/active/light/bg）按主色自动计算，无需手填
   用法:页面引入本文件即可，自动初始化；也可手动 ThemeKit.init()
   ================================================================== */
(function (global) {
  'use strict';

  var DEFAULT_PRIMARY = '#165DFF';
  var DEFAULT_BG_PAGE = '#F5F7FA';
  var DEFAULT_BG_CARD = '#FFFFFF';

  /* ---------- 颜色工具 ---------- */
  function hexToRgb(hex) {
    var h = String(hex || '').replace('#', '');
    if (h.length === 3) { h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]; }
    if (!/^[0-9a-fA-F]{6}$/.test(h)) { return null; }
    return {
      r: parseInt(h.substr(0, 2), 16),
      g: parseInt(h.substr(2, 2), 16),
      b: parseInt(h.substr(4, 2), 16)
    };
  }

  function rgbToHex(r, g, b) {
    return '#' + [r, g, b].map(function (v) {
      var s = Math.max(0, Math.min(255, Math.round(v))).toString(16);
      return s.length === 1 ? '0' + s : s;
    }).join('').toUpperCase();
  }

  function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b);
    var h = 0, s = 0, l = (max + min) / 2;
    var d = max - min;
    if (d !== 0) {
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      if (max === r) { h = (g - b) / d + (g < b ? 6 : 0); }
      else if (max === g) { h = (b - r) / d + 2; }
      else { h = (r - g) / d + 4; }
      h /= 6;
    }
    return { h: h * 360, s: s * 100, l: l * 100 };
  }

  function hue2rgb(p, q, t) {
    if (t < 0) { t += 1; }
    if (t > 1) { t -= 1; }
    if (t < 1 / 6) { return p + (q - p) * 6 * t; }
    if (t < 1 / 2) { return q; }
    if (t < 2 / 3) { return p + (q - p) * (2 / 3 - t) * 6; }
    return p;
  }

  function hslToRgb(h, s, l) {
    h /= 360; s /= 100; l /= 100;
    if (s === 0) {
      var v = l * 255;
      return { r: v, g: v, b: v };
    }
    var q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    var p = 2 * l - q;
    return {
      r: hue2rgb(p, q, h + 1 / 3) * 255,
      g: hue2rgb(p, q, h) * 255,
      b: hue2rgb(p, q, h - 1 / 3) * 255
    };
  }

  function hexToRgba(hex, alpha) {
    var rgb = hexToRgb(hex);
    if (!rgb) { return 'rgba(22,93,255,' + alpha + ')'; }
    return 'rgba(' + rgb.r + ',' + rgb.g + ',' + rgb.b + ',' + alpha + ')';
  }
  /* ---------- 派生色计算 ---------- */
  function deriveColors(primary) {
    var rgb = hexToRgb(primary);
    if (!rgb) { rgb = hexToRgb(DEFAULT_PRIMARY); primary = DEFAULT_PRIMARY; }
    var hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
    var h = hsl.h, s = hsl.s, l = hsl.l;

    function shift(dl) {
      var c = hslToRgb(h, s, Math.max(0, Math.min(100, l + dl)));
      return rgbToHex(c.r, c.g, c.b);
    }
    function withLightness(nl, ns) {
      var c = hslToRgb(h, ns === undefined ? s : ns, nl);
      return rgbToHex(c.r, c.g, c.b);
    }
    return {
      primary: rgbToHex(rgb.r, rgb.g, rgb.b),
      hover: shift(8),
      active: shift(-10),
      light: withLightness(Math.min(94, l + (100 - l) * 0.82), Math.min(s, 92)),
      bg: withLightness(Math.min(98, l + (100 - l) * 0.94), Math.min(s, 90)),
      shadow: hexToRgba(primary, 0.18)
    };
  }

  /* ---------- 注入 CSS 变量 ---------- */
  function applyColors(colors) {
    var root = document.documentElement;
    root.style.setProperty('--primary', colors.primary);
    /* RGB通道值:供Tailwind类页的透明度变体（bg-primary/10等）跟随主题改色 */
    var rgb = hexToRgb(colors.primary) || hexToRgb(DEFAULT_PRIMARY);
    root.style.setProperty('--primary-rgb', rgb.r + ',' + rgb.g + ',' + rgb.b);
    /* RGB空格格式值:供Tailwind的<alpha-value>语法使用（逗号格式与斜杠alpha混用属非法CSS，会导致主色类整条失效） */
    root.style.setProperty('--primary-rgb-space', rgb.r + ' ' + rgb.g + ' ' + rgb.b);
    root.style.setProperty('--primary-hover', colors.hover);
    root.style.setProperty('--primary-active', colors.active);
    root.style.setProperty('--primary-light', colors.light);
    root.style.setProperty('--primary-bg', colors.bg);
    root.style.setProperty('--shadow-primary', '0 4px 16px ' + colors.shadow);
  }

  /* ---------- 注入底色变量（界面底色/卡片底色） ---------- */
  function applyBgColors(bgPage, bgCard) {
    var root = document.documentElement;
    var p = (bgPage && hexToRgb(bgPage)) ? bgPage : DEFAULT_BG_PAGE;
    var c = (bgCard && hexToRgb(bgCard)) ? bgCard : DEFAULT_BG_CARD;
    root.style.setProperty('--bg-page', p);
    root.style.setProperty('--bg-card', c);
  }

  /* ---------- 读取配置主题色（主色+界面底色+卡片底色） ---------- */
  function fetchTheme() {
    return new Promise(function (resolve) {
      var done = false;
      function fallback() {
        return { primary: DEFAULT_PRIMARY, bgPage: DEFAULT_BG_PAGE, bgCard: DEFAULT_BG_CARD };
      }
      var timer = setTimeout(function () {
        if (!done) { done = true; resolve(fallback()); }
      }, 2500);

      function finish(theme) {
        if (done) { return; }
        done = true;
        clearTimeout(timer);
        resolve(theme && theme.primary ? theme : fallback());
      }

      try {
        var url = '/api/config/get';
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.timeout = 2500;
        xhr.onreadystatechange = function () {
          if (xhr.readyState !== 4) { return; }
          try {
            var data = JSON.parse(xhr.responseText || '{}');
            var cfg = (data && data.data) ? data.data : (data || {});
            finish({
              primary: (cfg.theme_primary_color && hexToRgb(cfg.theme_primary_color)) ? cfg.theme_primary_color : DEFAULT_PRIMARY,
              bgPage: (cfg.theme_bg_page && hexToRgb(cfg.theme_bg_page)) ? cfg.theme_bg_page : DEFAULT_BG_PAGE,
              bgCard: (cfg.theme_bg_card && hexToRgb(cfg.theme_bg_card)) ? cfg.theme_bg_card : DEFAULT_BG_CARD
            });
          } catch (e) { finish(fallback()); }
        };
        xhr.onerror = function () { finish(fallback()); };
        xhr.ontimeout = function () { finish(fallback()); };
        xhr.send();
      } catch (e) {
        finish(fallback());
      }
    });
  }

  /* ---------- 跨窗口同步:配置值快照 + 轻轮询（阶段④） ---------- */
  /* 仅当"从配置读到的值"发生变化时才应用，避免覆盖配置页未保存的实时预览；
     Qt 悬浮窗为独立窗口收不到 postMessage 广播，靠本轮询补齐同步（0~4秒延迟）。 */
  var lastConfigKey = '';
  var pollTimer = null;
  function themeKey(t) {
    t = t || {};
    return [t.primary || DEFAULT_PRIMARY, t.bgPage || DEFAULT_BG_PAGE, t.bgCard || DEFAULT_BG_CARD].join('|');
  }

  /* ---------- 首屏防闪烁:同步应用本地缓存的主题色 ---------- */
  /* 本文件在 <head> 中同步加载，此处同步读 localStorage 后立即写入 CSS 变量，
     可在浏览器首次绘制(body 渲染)前生效，避免等待异步接口期间闪现默认经典蓝。
     缓存仅在 fetchTheme 成功读到真实配置后回写，配置页未保存的预览色不会污染缓存。 */
  var THEME_CACHE_KEY = 'gzt_theme_cache';
  var hasCachedTheme = false;
  function applyCachedTheme() {
    try {
      var raw = localStorage.getItem(THEME_CACHE_KEY);
      if (!raw) { return; }
      var t = JSON.parse(raw) || {};
      if (!t.primary || !hexToRgb(t.primary)) { return; }
      applyColors(deriveColors(t.primary));
      applyBgColors(t.bgPage, t.bgCard);
      lastConfigKey = themeKey(t);
      hasCachedTheme = true;
    } catch (e) { hasCachedTheme = false; }
  }
  applyCachedTheme();
  function startPolling() {
    if (pollTimer) { return; }
    pollTimer = setInterval(function () {
      fetchTheme().then(function (theme) {
        var key = themeKey(theme);
        if (key !== lastConfigKey) {
          lastConfigKey = key;
          ThemeKit.setTheme(theme);
          try { localStorage.setItem(THEME_CACHE_KEY, JSON.stringify(theme)); } catch (e) {}
        }
      });
    }, 4000);
  }

  /* ---------- 对外接口 ---------- */
  var ThemeKit = {
    DEFAULT_PRIMARY: DEFAULT_PRIMARY,
    DEFAULT_BG_PAGE: DEFAULT_BG_PAGE,
    DEFAULT_BG_CARD: DEFAULT_BG_CARD,
    hexToRgb: hexToRgb,
    hexToRgba: hexToRgba,
    deriveColors: deriveColors,
    applyColors: applyColors,
    applyBgColors: applyBgColors,
    /* 手动设置主色（配置页实时预览用，保留旧接口） */
    setPrimary: function (primary) {
      var colors = deriveColors(primary);
      applyColors(colors);
      return colors;
    },
    /* 一次性设置主色+界面底色+卡片底色（配置页/跨iframe广播用） */
    setTheme: function (opt) {
      opt = opt || {};
      var colors = deriveColors(opt.primary || DEFAULT_PRIMARY);
      applyColors(colors);
      applyBgColors(opt.bgPage, opt.bgCard);
      return colors;
    },
    /* 读取配置并应用;有缓存直接用缓存色起帧,无缓存才落默认值再覆写 */
    init: function () {
      if (!hasCachedTheme) {
        applyColors(deriveColors(DEFAULT_PRIMARY));
        applyBgColors(DEFAULT_BG_PAGE, DEFAULT_BG_CARD);
      }
      return fetchTheme().then(function (theme) {
        var colors = deriveColors(theme.primary);
        applyColors(colors);
        applyBgColors(theme.bgPage, theme.bgCard);
        lastConfigKey = themeKey(theme);
        try { localStorage.setItem(THEME_CACHE_KEY, JSON.stringify(theme)); } catch (e) {}
        startPolling();
        return colors;
      });
    }
  };

  global.ThemeKit = ThemeKit;

  /* 跨 iframe 主题广播:收到 themeSync 消息即应用（11个页面统一受益） */
  window.addEventListener('message', function (e) {
    var d = e && e.data;
    if (d && d.type === 'themeSync') {
      ThemeKit.setTheme({ primary: d.primary, bgPage: d.bgPage, bgCard: d.bgCard });
    }
  });

  /* 自动初始化:DOM 就绪即执行 */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { ThemeKit.init(); });
  } else {
    ThemeKit.init();
  }
})(window);