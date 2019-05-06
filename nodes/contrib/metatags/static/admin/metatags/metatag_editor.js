/**
 * jQuery Metatag form textarea field.
 * @source https://github.org/sakkada/django-nodes
 * @author Murat Guchetl (gmurka AT gmail DOT com)
 * @requires jQuery
 *
 * Copyright (c) 2019, Murat Guchetl
 * All rights reserved.
 *
 * Licensed under the MIT License
 */

// require jQuery
(function($) {
  $(document).ready(function() {
    $('.editor_metatag').adjustableHeightField();
  });
})(django && django.jQuery ? django.jQuery : jQuery); // django.jQuery also support
