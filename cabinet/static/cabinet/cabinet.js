/* global django */
django.jQuery(($) => {
  if (!document.body.classList.contains("change-list")) return

  // Remove filtered class so that module uses horizontal space better
  $(".module.filtered").removeClass("filtered")

  // Hardcoded result list HTML if there are no files at all (for example in
  // the root folder)
  if (!$("#result_list").length) {
    const rl = document.getElementById("cabinet-result-list")
    $(rl).before(rl.innerHTML)
  }

  // Prepend folders to result list
  $("#result_list>tbody").prepend(
    document.getElementById("cabinet-folder-list").innerHTML,
  )

  let dragCounter = 0
  const results = $(".results")
  const folder = window.location.href.match(/folder__id__exact=(\d+)/)

  if (!folder) {
    $(".cabinet-upload-hint").remove()
    return
  }

  results
    .on("drag dragstart dragend dragover dragenter dragleave drop", (e) => {
      e.preventDefault()
      e.stopPropagation()
    })
    .on("dragover dragenter", () => {
      ++dragCounter
      results.addClass("dragover")
    })
    .on("dragleave dragend", () => {
      if (--dragCounter <= 0) results.removeClass("dragover")
    })
    .on("mouseleave mouseout drop", () => {
      dragCounter = 0
      results.removeClass("dragover")
    })
    .on("drop", (e) => {
      dragCounter = 0
      results.removeClass("dragover")
      uploadFiles(e.originalEvent.dataTransfer.files)
    })

  const cabinetUpload = $("#cabinet-upload")
  const cabinetUploadInput = cabinetUpload.find("input")
  cabinetUpload.on("click", "a", (e) => {
    e.preventDefault()
    cabinetUploadInput.trigger("click")
  })
  cabinetUploadInput.on("change", (e) => {
    uploadFiles(e.target.files)
  })

  function uploadFiles(files) {
    let success = 0
    const progress = $(`<div class="progress">0 / ${files.length}</div>`)

    progress.appendTo(results)

    for (const file of files) {
      const d = new FormData()
      d.append(
        "csrfmiddlewaretoken",
        $("input[name=csrfmiddlewaretoken]").val(),
      )
      d.append("folder", folder[1])
      d.append("file", file)

      $.ajax({
        url: "./upload/",
        type: "POST",
        data: d,
        contentType: false,
        processData: false,
        success: () => {
          progress.html(`${++success} / ${files.length}`)
          if (success >= files.length) {
            window.location.reload()
          }
        },
        xhr: () => {
          const xhr = new XMLHttpRequest()
          xhr.upload.addEventListener(
            "progress",
            (e) => {
              if (e.lengthComputable) {
                progress.html(
                  `${Math.round((e.loaded / e.total) * 100)}% of ${success + 1} / ${files.length}`,
                )
              }
            },
            false,
          )
          return xhr
        },
      })
    }
  }
})
