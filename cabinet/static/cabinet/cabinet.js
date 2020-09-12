/* global django */
django.jQuery(function ($) {
  if (!document.body.classList.contains("change-list")) return;

  // Remove filtered class so that module uses horizontal space better
  $(".module.filtered").removeClass("filtered");

  // Hardcoded result list HTML if there are no files at all (for example in
  // the root folder)
  if (!$("#result_list").length) {
    var rl = document.getElementById("cabinet-result-list");
    $(rl).before(rl.innerHTML);
  }

  // Prepend folders to result list
  $("#result_list>tbody").prepend(
    document.getElementById("cabinet-folder-list").innerHTML
  );

  var dragCounter = 0,
    results = $(".results"),
    folder = window.location.href.match(/folder__id__exact=(\d+)/);

  if (!folder) {
    $(".cabinet-upload-hint").remove();
    return;
  }

  results
    .on("drag dragstart dragend dragover dragenter dragleave drop", function (
      e
    ) {
      e.preventDefault();
      e.stopPropagation();
    })
    .on("dragover dragenter", function () {
      ++dragCounter;
      results.addClass("dragover");
    })
    .on("dragleave dragend", function () {
      if (--dragCounter <= 0) results.removeClass("dragover");
    })
    .on("mouseleave mouseout drop", function () {
      dragCounter = 0;
      results.removeClass("dragover");
    })
    .on("drop", function (e) {
      dragCounter = 0;
      results.removeClass("dragover");
      uploadFiles(e.originalEvent.dataTransfer.files);
    });

  var cabinetUpload = $("#cabinet-upload"),
    cabinetUploadInput = cabinetUpload.find("input");
  cabinetUpload.on("click", "a", function (e) {
    e.preventDefault();
    cabinetUploadInput.trigger("click");
  });
  cabinetUploadInput.on("change", function (e) {
    uploadFiles(e.target.files);
  });

  function uploadFiles(files) {
    var success = 0,
      progress = $('<div class="progress">0 / ' + files.length + "</div>");

    progress.appendTo(results);

    for (var i = 0; i < files.length; ++i) {
      var d = new FormData();
      d.append(
        "csrfmiddlewaretoken",
        $("input[name=csrfmiddlewaretoken]").val()
      );
      d.append("folder", folder[1]);
      d.append("file", files[i]);

      $.ajax({
        url: "./upload/",
        type: "POST",
        data: d,
        contentType: false,
        processData: false,
        success: function () {
          progress.html("" + ++success + " / " + files.length);
          if (success >= files.length) {
            window.location.reload();
          }
        },
        xhr: function () {
          var xhr = new XMLHttpRequest();
          xhr.upload.addEventListener(
            "progress",
            function (e) {
              if (e.lengthComputable) {
                progress.html(
                  Math.round((e.loaded / e.total) * 100) +
                    "% of " +
                    (success + 1) +
                    " / " +
                    files.length
                );
              }
            },
            false
          );
          return xhr;
        },
      });
    }
  }
});
