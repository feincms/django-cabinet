Change log
==========

`Next version`_
~~~~~~~~~~~~~~~

`0.6`_ (2018-03-18)
~~~~~~~~~~~~~~~~~~~

- Changed ``admin_details`` to not include superfluous ``<br>`` tags.
- Changed the ``accept_file`` methods on file mixins to return bools and
  not raise exceptions.
- Fixed the ``OverwriteMixin`` to call ``delete_files`` so that e.g.
  the ``versatileimagefield`` gets a chance of removing stale
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

.. _0.1: https://github.com/matthiask/django-cabinet/commit/4b8747afd
.. _0.2: https://github.com/matthiask/django-cabinet/compare/0.1...0.2
.. _0.3: https://github.com/matthiask/django-cabinet/compare/0.2...0.3
.. _0.4: https://github.com/matthiask/django-cabinet/compare/0.3...0.4
.. _0.5: https://github.com/matthiask/django-cabinet/compare/0.4...0.5
.. _0.6: https://github.com/matthiask/django-cabinet/compare/0.5...0.6
.. _Next version: https://github.com/matthiask/django-cabinet/compare/0.6...master
