django.jQuery(function($) {
  if (!document.body.classList.contains('change-list'))
    return;

  // Remove filtered class so that module uses horizontal space better
  $('.module.filtered').removeClass('filtered');

  // Hardcoded result list HTML if there are no files at all (for example in
  // the root folder)
  if (!$('#result_list').length) {
    var rl = document.getElementById('cabinet-result-list');
    $(rl).before(rl.innerHTML);
  }

  // Prepend folders to result list
  $('#result_list>tbody').prepend(document.getElementById('cabinet-folder-list').innerHTML);

  // Search searches all files; remove folder filter
  $('#changelist-search input[name=folder__id__exact]').remove();

  var dragCounter = 0,
    results = $('.results');

  results.on('drag dragstart dragend dragover dragenter dragleave drop', function(e) {
    e.preventDefault();
    e.stopPropagation();
  }).on('dragover dragenter', function(e) {
    ++dragCounter;
    results.addClass('dragover');
  }).on('dragleave dragend', function(e) {
    if (--dragCounter <= 0)
      results.removeClass('dragover');
  }).on('mouseleave mouseout drop', function(e) {
    dragCounter = 0;
    results.removeClass('dragover');
  }).on('drop', function(e) {
    dragCounter = 0;
    results.removeClass('dragover');

    var files = e.originalEvent.dataTransfer.files,
      success = 0,
      progress = $('<div class="progress">0 / ' + files.length + '</div>');

    progress.appendTo(results);

    console.log(progress);
    console.log(files);

    for (var i=0; i<files.length; ++i) {
      var d = new FormData();
      d.append('csrfmiddlewaretoken', $('input[name=csrfmiddlewaretoken]').val());
      d.append('folder', window.location.href.match(/folder__id__exact=(\d+)/)[1]);
      d.append('file', files[i]);

      $.ajax({
        url: './upload/',
        type: 'POST',
        data: d,
        contentType: false,
        processData: false,
        success: function() {
          progress.html('' + ++success + ' / ' + files.length);
          if (success >= files.length) {
            window.location.reload();
          }
        },
      });
    }
  });
});
