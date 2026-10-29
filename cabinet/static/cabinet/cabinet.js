/* global django */
django.jQuery((_$) => {
  // Folder tree: clicking the label/radio inside a <summary> would normally
  // toggle the <details> closed — prevent that and always open instead.
  document
    .querySelectorAll(".cabinet-folder-tree details > summary")
    .forEach((summary) => {
      summary.addEventListener("click", (e) => {
        if (e.target.closest("label")) {
          summary.closest("details").open = true
        }
      })
    })
})

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
  const folder = new URLSearchParams(window.location.search)
    .getAll("folder__id__exact")
    .at(-1)

  initFolderTree()
  initMoveFiles(folder)

  if (!folder || !/^\d+$/.test(folder)) {
    $(".cabinet-upload-hint").remove()
    return
  }

  results
    .on("drag dragstart dragend dragover dragenter dragleave drop", (e) => {
      // Moving files around is handled by initMoveFiles
      if (isMoveDrag(e.originalEvent)) return
      e.preventDefault()
      e.stopPropagation()
    })
    .on("dragover dragenter", (e) => {
      if (isMoveDrag(e.originalEvent)) return
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
      if (isMoveDrag(e.originalEvent)) return
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
    let done = 0
    const progress = $(`<div class="progress">0 / ${files.length}</div>`)

    progress.appendTo(results)

    for (const file of files) {
      const d = new FormData()
      d.append(
        "csrfmiddlewaretoken",
        $("input[name=csrfmiddlewaretoken]").val(),
      )
      d.append("folder", folder)
      d.append("file", file)

      $.ajax({
        url: "./upload/",
        type: "POST",
        data: d,
        contentType: false,
        processData: false,
        success: () => {
          progress.html(`${++success} / ${files.length}`)
        },
        error: () => {
          window.alert(`Upload of ${file.name} failed.`)
        },
        complete: () => {
          if (++done >= files.length) {
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

function initFolderTree() {
  // Load subfolders when expanding a folder in the tree for the first time,
  // either by clicking or by hovering over it while dragging files. The
  // toggle event doesn't bubble, therefore listen in the capture phase.
  document.addEventListener(
    "toggle",
    (e) => {
      const details = e.target
      if (!details.open || !details.matches?.("details[data-cabinet-lazy]")) {
        return
      }
      details.removeAttribute("data-cabinet-lazy")
      const href = details
        .querySelector(":scope > summary a")
        .getAttribute("href")

      fetch(`./folder-tree/${href}`, { credentials: "same-origin" })
        .then((response) => {
          if (!response.ok) throw new Error(response.statusText)
          return response.text()
        })
        .then((html) => {
          details.querySelector(":scope > ul").innerHTML = html
        })
        .catch(() => {
          details.setAttribute("data-cabinet-lazy", "")
          details.open = false
        })
    },
    true,
  )
}

const MOVE_TYPE = "application/x-cabinet-files"

function isMoveDrag(e) {
  return !!e.dataTransfer?.types.includes(MOVE_TYPE)
}

function initMoveFiles(currentFolder) {
  const csrfToken = document.querySelector(
    "input[name=csrfmiddlewaretoken]",
  )?.value
  if (!csrfToken) return

  const rows = document.querySelectorAll("#result_list tbody tr")
  for (const row of rows) {
    if (!row.querySelector("input.action-select")) continue
    row.draggable = true
  }

  // Drag all selected files if the dragged row is selected, the dragged row
  // only otherwise. Listen in the capture phase so that the upload handlers
  // already recognize the drag as a move.
  document.addEventListener(
    "dragstart",
    (e) => {
      const row = e.target.closest?.("#result_list tr[draggable=true]")
      if (!row) return

      const checkbox = row.querySelector("input.action-select")
      const ids = checkbox.checked
        ? [...document.querySelectorAll("input.action-select:checked")].map(
            (input) => input.value,
          )
        : [checkbox.value]

      e.dataTransfer.clearData()
      e.dataTransfer.setData(MOVE_TYPE, JSON.stringify(ids))
      e.dataTransfer.effectAllowed = "move"

      const image = document.createElement("div")
      image.className = "cabinet-drag-image"
      image.textContent =
        ids.length === 1
          ? row.querySelector(".field-admin_file_name")?.textContent.trim()
          : `${ids.length} files`
      document.body.append(image)
      e.dataTransfer.setDragImage(image, 0, 0)
      setTimeout(() => image.remove())
    },
    true,
  )

  const dropTarget = (e) => {
    const target = e.target.closest?.("[data-cabinet-folder]")
    if (!target || !isMoveDrag(e)) return null
    if (target.dataset.cabinetFolder === currentFolder) return null
    return target
  }

  for (const type of ["dragenter", "dragover"]) {
    document.addEventListener(type, (e) => {
      const target = dropTarget(e)
      if (!target) return
      e.preventDefault()
      e.dataTransfer.dropEffect = "move"
      target.classList.add("cabinet-dropover")
    })
  }

  document.addEventListener("dragleave", (e) => {
    const target = e.target.closest?.("[data-cabinet-folder]")
    if (target && !target.contains(e.relatedTarget)) {
      target.classList.remove("cabinet-dropover")
    }
  })

  document.addEventListener("drop", (e) => {
    const target = dropTarget(e)
    if (!target) return
    e.preventDefault()
    target.classList.remove("cabinet-dropover")

    const body = new FormData()
    body.append("csrfmiddlewaretoken", csrfToken)
    body.append("folder", target.dataset.cabinetFolder)
    for (const id of JSON.parse(e.dataTransfer.getData(MOVE_TYPE))) {
      body.append("files", id)
    }

    fetch("./move/", { method: "POST", body, credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw new Error(response.statusText)
        window.location.reload()
      })
      .catch((error) => {
        window.alert(`Moving files failed: ${error.message}`)
      })
  })

  // Expand collapsed folders in the tree when hovering over them for a
  // moment while dragging files
  let expandTarget = null
  let expandTimer = null
  const cancelExpand = () => {
    clearTimeout(expandTimer)
    expandTarget = expandTimer = null
  }

  document.addEventListener("dragover", (e) => {
    if (!isMoveDrag(e)) return
    const details = e.target.closest?.(
      ".cabinet-folder-tree details:not([open]) > summary",
    )?.parentElement
    if (details === expandTarget) return
    cancelExpand()
    if (!details) return
    expandTarget = details
    expandTimer = setTimeout(() => {
      details.open = true
      cancelExpand()
    }, 700)
  })
  document.addEventListener("dragend", cancelExpand)
  document.addEventListener("drop", cancelExpand)
}
