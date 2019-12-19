Change log
==========

`Next version`_
~~~~~~~~~~~~~~~


`0.10`_ (2019-12-19)
~~~~~~~~~~~~~~~~~~~~

- Changed files and folders to reuse more of django-tree-queries.
- Made our inline upload JavaScript specify its dependency on
  ``django.jQuery``.
- Verified compatibility with Django 3.0.
- Changed the abstract file model to protect files against cascading
  folder deletions.


`0.9`_ (2019-04-15)
~~~~~~~~~~~~~~~~~~~

- Changed ``CabinetForeignKey`` to reference the configured file model
  by default.
- Limited the maximum width of the inline folder select widget.
- Added tests for the ``CabinetForeignKey``.
- Hardened the file upload route a bit.
- Removed a leftover call to versatileimagefields'
  ``delete_all_created_images`` function.
- Improved test coverage, mainly by actually writing more tests.
- Changed ``reverse`` call sites to explicitly specify ``current_app``.
- Implemented optional autoselection of the last visited folder by
  explicitly specifying ``?folder__id__exact=last``.
- Made ``CabinetForeignKey`` automatically open the last folder for new
  files.
- Dropped compatibility with Django 1.8 again.
- Made our JS files' dependency on ``django.jQuery`` explicit.
- Raised the length of file fields from ``100`` to ``1000``.


`0.8`_ (2018-12-14)
~~~~~~~~~~~~~~~~~~~

- Fix a problem where newer Django versions would crash because of a
  missing ``inline_admin_formsets`` variable in the admin change form
  context.
- Fixed the folder hierarchy loop detection to not enter an infinite
  loop itself.
- Fixed the breadcrumbs parent folder links.
- Also prevented root folders with same name.
- Added django-tree-queries_ for helping manage the folder tree.
- Made search only search the current folder and its descendants.
- Changed ``OverwriteMixin`` to only overwrite files once as intended.
- Fixed a crash when moving several files at once with newer Django
  versions.
- Reinstated the PPOI functionality in the default file admin interface.
- Added a ``cabinet.fields.CabinetForeignKey`` drop-in replacement which
  extends the ``raw_id_fields`` administration interface with a direct
  upload facility.
- Added configuration to make running prettier and ESLint easy.
- Added compatibility with Django 1.8 so that migrating files from
  prehistoric django-filer versions gets easier.
- Added more visible UI to upload several files at once.
- Added timestamps to folders and files.
- Added support for using django-cabinet as a CKEditor filebrowser.
- Changed ``FileAdmin.get_fieldsets`` to automatically generate fitting
  fieldsets using the file mixins' verbose name and editable fields.
- Added a filter for only showing files of a certain type.
- Improved test coverage a bit and updated the documentation after
  actually using a swappable file model in a project.
- Fixed a crash when an invalid primary key was specified as a query
  parameter in the admin changelist.
- Modified responses when adding or editing files to always redirect to
  the containing folder instead of the root folder.
- Fixed a possible crash when setting ``_overwrite`` to true but
  uploading no new file.


`0.7`_ (2018-03-28)
~~~~~~~~~~~~~~~~~~~

- Switched the image field from django-versatileimagefield_ to
  django-imagefield_. The latter uses the same database layout
  as the former, but there are differences when it comes to image
  generation and generating thumbnail URLs.


`0.6`_ (2018-03-18)
~~~~~~~~~~~~~~~~~~~

- Changed ``admin_details`` to not include superfluous ``<br>`` tags.
- Changed the ``accept_file`` methods on file mixins to return bools and
  not raise exceptions.
- Fixed the ``OverwriteMixin`` to call ``delete_files`` so that e.g.
  the ``imagefield`` gets a chance of removing stale
  thumbnails.
- Dropped the useless ``AbstractFile``, and renamed ``AbstractFileBase``
  to ``AbstractFile``.
- Added a guide on how to swap out the file model.
- Added a hint to the files changelist that drag-drop upload is
  possible.
- Disabled the drag-drop upload on the root folder (which would not have
  worked anyway, because files cannot be added to the root folder).
- Added ``unify`` so that only one quoting style is used in the code.
- Changed the order of ``accept_file`` methods called to the order of
  ``FILE_FIELDS`` instead of the MRO (resp. the classes where the file
  fields are defined initially).
- Fixed the double saves in ``OverwriteMixin``, and hopefully avoided
  edge case-y problems with ``delete_files``.


`0.5`_ (2018-03-13)
~~~~~~~~~~~~~~~~~~~

- Made the folder CRUD functionality preserve query parameters so that
  ``raw_id_fields`` popups work seamlessly.
- Fixed the changelist to not crash when images are broken.
- Changed the admin fieldsets to only show fields related to one file
  type when a cabinet file is filled in already.
- Fixed a bug where adding subfolders would succeed, but redirect to the
  root folder.
- Added an admin action for moving multiple files at once to a different
  folder.


`0.4`_ (2017-07-04)
~~~~~~~~~~~~~~~~~~~

- Made file model mixins determine themselves whether they can accept an
  upload or not.
- Refactoring and code cleanups.
- Tweaked the file list a bit.


`0.3`_ (2017-06-21)
~~~~~~~~~~~~~~~~~~~

- Added upload progress (only files, not bytes).
- Implemented cleaning of storage when deleting and replacing files.


`0.2`_ (2017-06-21)
~~~~~~~~~~~~~~~~~~~

- Allow replacing files remotely.
- Added caption, copyright and alt text fields.
- Also show folder breadcrumbs when adding files.
- Drag-drop upload of files directly into the folder view.


`0.1`_ (2017-06-20)
~~~~~~~~~~~~~~~~~~~

- Initial public version.

.. _django-imagefield: https://django-imagefield.readthedocs.io/
.. _django-tree-queries: https://github.com/matthiask/django-tree-queries/
.. _django-versatileimagefield: https://django-versatileimagefield.readthedocs.io/

.. _0.1: https://github.com/matthiask/django-cabinet/commit/4b8747afd
.. _0.2: https://github.com/matthiask/django-cabinet/compare/0.1...0.2
.. _0.3: https://github.com/matthiask/django-cabinet/compare/0.2...0.3
.. _0.4: https://github.com/matthiask/django-cabinet/compare/0.3...0.4
.. _0.5: https://github.com/matthiask/django-cabinet/compare/0.4...0.5
.. _0.6: https://github.com/matthiask/django-cabinet/compare/0.5...0.6
.. _0.7: https://github.com/matthiask/django-cabinet/compare/0.6...0.7
.. _0.8: https://github.com/matthiask/django-cabinet/compare/0.7...0.8
.. _0.9: https://github.com/matthiask/django-cabinet/compare/0.8...0.9
.. _0.10: https://github.com/matthiask/django-cabinet/compare/0.9...0.10
.. _Next version: https://github.com/matthiask/django-cabinet/compare/0.10...master
