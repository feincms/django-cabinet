django.jQuery(function($) {
  $(document.body).on("click", "[data-ckeditor-function]", function(e) {
    e.preventDefault();
    opener.CKEDITOR.tools.callFunction(parseInt(this.dataset.ckeditorFunction, 10), this.getAttribute("href"));
    window.close();
  });
});
