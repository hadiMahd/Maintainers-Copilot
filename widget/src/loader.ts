/**
 * Maintainer Copilot Widget Loader
 *
 * Usage:
 *   <script src="https://your-server/widget/loader.js" data-widget-id="wid-xxx"></script>
 *
 * This loader:
 * 1. Reads the `data-widget-id` attribute from its own <script> tag
 * 2. Injects a hidden iframe pointing to `/widget/frame/{widget_id}`
 * 3. Listens for `postMessage` resize events from the iframe
 * 4. Never exposes widget IDs in query strings
 */

(function () {
  "use strict";

  var SCRIPT_ATTR = "data-widget-id";
  var RESIZE_EVENT = "maintainer-copilot-widget:resize";
  var IFRAME_ID = "maintainer-copilot-widget-frame";

  /**
   * Find the loader script element that loaded this file.
   */
  function findLoaderScript() {
    var scripts = document.querySelectorAll("script[" + SCRIPT_ATTR + "]");
    for (var i = 0; i < scripts.length; i++) {
      var src = scripts[i].src || "";
      if (src.indexOf("loader.js") !== -1) {
        return scripts[i];
      }
    }
    return null;
  }

  /**
   * Resolve the base URL from the loader script src.
   */
  function resolveBaseUrl(scriptSrc) {
    var idx = scriptSrc.indexOf("/widget/loader.js");
    if (idx !== -1) {
      return scriptSrc.substring(0, idx);
    }
    return "";
  }

  /**
   * Create and inject the widget iframe.
   */
  function injectIframe(baseUrl, widgetId) {
    var existing = document.getElementById(IFRAME_ID);
    if (existing) {
      return;
    }

    var iframe = document.createElement("iframe");
    iframe.id = IFRAME_ID;
    iframe.src = baseUrl + "/widget/frame/" + encodeURIComponent(widgetId);
    iframe.style.cssText =
      "position:fixed;bottom:20px;right:20px;width:380px;height:500px;" +
      "border:none;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,0.15);" +
      "z-index:2147483647;background:#fff;";
    iframe.allow = "clipboard-write";
    iframe.title = "Maintainer Copilot Widget";

    document.body.appendChild(iframe);
    return iframe;
  }

  /**
   * Handle resize messages from the iframe.
   * Only accepts messages with the expected event type and origin.
   */
  function setupMessageListener(iframe) {
    window.addEventListener("message", function (event) {
      if (!event.data || typeof event.data !== "object") {
        return;
      }
      if (event.data.type !== RESIZE_EVENT) {
        return;
      }
      if (event.source !== iframe.contentWindow) {
        return;
      }
      var height = event.data.height;
      var width = event.data.width;
      if (typeof height === "number" && height > 0) {
        iframe.style.height = height + "px";
      }
      if (typeof width === "number" && width > 0) {
        iframe.style.width = width + "px";
      }
    });
  }

  /**
   * Main entry point.
   */
  function init() {
    if (typeof document === "undefined" || !document.body) {
      document.addEventListener("DOMContentLoaded", init);
      return;
    }

    var script = findLoaderScript();
    if (!script) {
      console.warn("[maintainer-copilot] No script tag with data-widget-id found");
      return;
    }

    var widgetId = script.getAttribute(SCRIPT_ATTR);
    if (!widgetId) {
      console.warn("[maintainer-copilot] data-widget-id attribute is empty");
      return;
    }

    var baseUrl = resolveBaseUrl(script.src || "");
    var iframe = injectIframe(baseUrl, widgetId);
    if (iframe) {
      setupMessageListener(iframe);
    }
  }

  init();
})();
