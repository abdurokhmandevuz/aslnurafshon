(function () {
  let scanner = null;
  let active = false;
  let lastCode = "";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function $(selector) {
    return document.querySelector(selector);
  }

  function show(el) {
    if (el) el.classList.remove("hidden");
  }

  function hide(el) {
    if (el) el.classList.add("hidden");
  }

  function setResult(code, message, existingUrl) {
    const box = $("#barcode-scanner-result");
    $("#barcode-scanner-code").textContent = code;
    $("#barcode-scanner-message").textContent = message || "";
    const link = $("#barcode-scanner-existing");
    if (existingUrl) {
      link.href = existingUrl;
      show(link);
    } else {
      hide(link);
    }
    show(box);
  }

  function getInlineInput(fieldName) {
    let input = document.querySelector(`input[name^="variants-"][name$="-${fieldName}"]:not([name*="__prefix__"])`);
    if (input) return input;

    const addRow = document.querySelector("#variants-group .add-row a, .inline-group .add-row a");
    if (addRow) addRow.click();

    const inputs = Array.from(document.querySelectorAll(`input[name^="variants-"][name$="-${fieldName}"]:not([name*="__prefix__"])`));
    return inputs.find((item) => !item.value) || inputs[inputs.length - 1] || null;
  }

  function fillForm(data) {
    const nameInput = $("#id_name");
    if (nameInput && data.product_name && !nameInput.value.trim()) {
      nameInput.value = data.product_name;
      nameInput.dispatchEvent(new Event("change", { bubbles: true }));
    }

    const barcodeInput = getInlineInput("barcode");
    if (barcodeInput) {
      barcodeInput.value = data.barcode || lastCode;
      barcodeInput.dispatchEvent(new Event("change", { bubbles: true }));
    }

    const labelInput = getInlineInput("label");
    if (labelInput && data.label && !labelInput.value.trim()) {
      labelInput.value = data.label;
      labelInput.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  async function lookupBarcode(code) {
    const url = `/admin/catalog/product/barcode-lookup/?barcode=${encodeURIComponent(code)}`;
    const response = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!response.ok) throw new Error("lookup_failed");
    return response.json();
  }

  async function onScanSuccess(code) {
    if (!code || code === lastCode) return;
    lastCode = code;
    if (navigator.vibrate) navigator.vibrate(80);

    try {
      const data = await lookupBarcode(code);
      fillForm(data);
      setResult(
        code,
        data.message || "Shtrix kod inputga tushirildi.",
        data.exists ? data.product_admin_url : ""
      );
      await stopScanner();
    } catch (error) {
      fillForm({ barcode: code });
      setResult(code, "Shtrix kod o‘qildi. Qolgan maydonlarni o‘zingiz to‘ldiring.", "");
      await stopScanner();
    }
  }

  async function startScanner() {
    if (active) return;
    const panel = $("#barcode-scanner-panel");
    show(panel);
    lastCode = "";

    if (!window.Html5Qrcode) {
      setResult("", "Scanner kutubxonasi yuklanmadi. Internetni tekshiring.", "");
      return;
    }

    const formats = window.Html5QrcodeSupportedFormats
      ? [
          Html5QrcodeSupportedFormats.EAN_13,
          Html5QrcodeSupportedFormats.EAN_8,
          Html5QrcodeSupportedFormats.UPC_A,
          Html5QrcodeSupportedFormats.UPC_E,
          Html5QrcodeSupportedFormats.CODE_128,
          Html5QrcodeSupportedFormats.CODE_39,
          Html5QrcodeSupportedFormats.ITF,
        ]
      : undefined;

    scanner = new Html5Qrcode("barcode-scanner-reader", { formatsToSupport: formats });
    active = true;
    const config = {
      fps: 20,
      qrbox: function (width, height) {
        return {
          width: Math.round(width * 0.92),
          height: Math.round(Math.min(height * 0.42, 260)),
        };
      },
      aspectRatio: 1.777778,
    };

    try {
      await scanner.start(
        { facingMode: "environment" },
        config,
        onScanSuccess,
        function () {}
      );
    } catch (error) {
      active = false;
      setResult("", "Kamerani yoqib bo‘lmadi. Brauzer ruxsatini tekshiring.", "");
    }
  }

  async function stopScanner() {
    if (!scanner || !active) return;
    try {
      await scanner.stop();
      await scanner.clear();
    } catch (error) {
      // Scanner may already be stopped.
    }
    active = false;
    scanner = null;
  }

  ready(function () {
    const openButton = $("#barcode-scanner-open");
    const closeButton = $("#barcode-scanner-close");
    if (openButton) openButton.addEventListener("click", startScanner);
    if (closeButton) {
      closeButton.addEventListener("click", async function () {
        await stopScanner();
        hide($("#barcode-scanner-panel"));
      });
    }
  });
})();
