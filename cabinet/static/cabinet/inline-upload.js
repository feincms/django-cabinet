/* global django */
django.jQuery(($) => {
  $(".cabinet-inline-wrap").each(function () {
    const wrap = $(this)
    wrap
      .find("input[type='file']")
      .attr("disabled", !wrap.find(".cabinet-inline-upload select").val())
  })

  $(document.body).on("change", ".cabinet-inline-upload select", function () {
    const wrap = $(this).closest(".cabinet-inline-wrap")
    wrap.find("input[type='file']").attr("disabled", !this.value)
  })

  $(document.body).on("change", ".cabinet-inline-upload input", function (e) {
    doUpload($(this).closest(".cabinet-inline-wrap"), e.target.files[0])
  })

  function doUpload(wrap, file) {
    const d = new FormData()
    d.append("csrfmiddlewaretoken", $("input[name=csrfmiddlewaretoken]").val())
    d.append("folder", wrap.find("select").val())
    d.append("file", file)

    $.ajax({
      url: wrap.data("url"),
      type: "POST",
      data: d,
      contentType: false, // request
      processData: false, // request
      dataType: "json", // response
      success: (data) => {
        wrap.find(".cabinet-inline-field input").val(data.pk)
        wrap.find(".cabinet-inline-upload input").val("")
        wrap.find(".cabinet-inline-field strong>a").text(data.name)
      },
    })
  }
})
