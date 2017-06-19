=========================================
django-cabinet - Media library for Django
=========================================

.. image:: https://travis-ci.org/matthiask/django-cabinet.png?branch=master
   :target: https://travis-ci.org/matthiask/django-cabinet

.. image:: _static/root-folders.png

.. image:: _static/files-and-folders.png

.. image:: _static/image-ppoi.png

django-cabinet is a media library for Django implemented while trying to
write as little code as possible to keep maintenance at a minimum.


Goals
=====

- Be as minimal as possible
- Avoid settings at all costs
- Stay extensible


Non-goals
=========

- Take over the world


Installation
============

- ``pip install django-cabinet``
- Add ``cabinet`` and ``versatileimagefield`` to your ``INSTALLED_APPS``
- Maybe replace the file model by setting ``CABINET_FILE_MODEL``, but the
  default should be fine for most uses.


High-level overview
===================

...

.. include:: ../CHANGELOG.rst
