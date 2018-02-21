Change log
==========

`Next version`_
~~~~~~~~~~~~~~~

- Made the folder CRUD functionality preserve query parameters so that
  ``raw_id_fields`` popups work seamlessly.
- Fixed the changelist to not crash when images are broken.


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
.. _Next version: https://github.com/matthiask/django-cabinet/compare/0.4...master
