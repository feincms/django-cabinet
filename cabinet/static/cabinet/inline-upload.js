/* global django */
django.jQuery(function ($) {
  $(".cabinet-inline-wrap").each(function () {
    var wrap = $(this);
    wrap
      .find("input[type='file']")
      .attr("disabled", !wrap.find(".cabinet-inline-upload select").val());
  });

  $(document.body).on("change", ".cabinet-inline-upload select", function () {
    var wrap = $(this).closest(".cabinet-inline-wrap");
    wrap.find("input[type='file']").attr("disabled", !this.value);
  });

  $(document.body).on("change", ".cabinet-inline-upload input", function (e) {
    doUpload($(this).closest(".cabinet-inline-wrap"), e.target.files[0]);
  });

  function doUpload(wrap, file) {
    var d = new FormData();
    d.append("csrfmiddlewaretoken", $("input[name=csrfmiddlewaretoken]").val());
    d.append("folder", wrap.find("select").val());
    d.append("file", file);

    $.ajax({
      url: wrap.data("url"),
      type: "POST",
      data: d,
      contentType: false, // request
      processData: false, // request
      dataType: "json", // response
      success: function (data) {
        wrap.find(".cabinet-inline-field input").val(data.pk);
        wrap.find(".cabinet-inline-upload input").val("");
        wrap.find(".cabinet-inline-field strong>a").text(data.name);
      },
    });
  }
});
