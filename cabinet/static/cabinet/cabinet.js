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
});
