=========================================
django-cabinet - Media library for Django
=========================================

.. image:: https://travis-ci.org/matthiask/django-cabinet.png?branch=master
   :target: https://travis-ci.org/matthiask/django-cabinet

django-cabinet is a media library for Django implemented while trying to
write as little code as possible to keep maintenance at a minimum. At
the time of writing the projects consists of less than 1000 lines of
code (excluding tests), but still offers hierarchical folders,
downloads, images with primary point of interest (courtesy of
django-versatileimagefield_) and drag-drop uploading of files directly
into the folder view.


Screenshots
===========

.. figure:: _static/root-folders.png

   List of root folders

.. figure:: _static/files-and-folders.png

   Folder view with subfolders and files

.. figure:: _static/image-ppoi.png

   File details with primary point of interest


Installation
============

- ``pip install django-cabinet``
- Add ``cabinet`` and ``versatileimagefield`` to your ``INSTALLED_APPS``
- Maybe replace the file model by setting ``CABINET_FILE_MODEL``, but the
  default should be fine for most uses.


High-level overview
===================

django-cabinet comes with two concrete models, ``cabinet.File`` and
``cabinet.Folder``.

**Folders** can be nested into a hierarchy. The folder
tree intentionally uses an adjacency list model without any query
optimization strategies (such as nested sets or recursive CTEs) so that
no dependencies are necessary.

**Files** by default have two file fields, one for images based on
django-versatileimagefield_ and one for downloads, a standard Django
``FileField``. Exactly one field has to be filled in. Files can only be
added to folders; files can never exist in the root folder.


.. include:: ../CHANGELOG.rst

.. _django-versatileimagefield: https://django-versatileimagefield.readthedocs.io/
