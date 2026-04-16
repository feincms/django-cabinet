/* global django */
django.jQuery(($) => {
  $(document.body).on("click", "[data-ckeditor-function]", function (e) {
    e.preventDefault()
    opener.CKEDITOR.tools.callFunction(
      Number.parseInt(this.getAttribute("data-ckeditor-function"), 10),
      this.getAttribute("href"),
      JSON.parse(this.getAttribute("data-ckeditor-data")),
    )
    window.close()
  })
})
