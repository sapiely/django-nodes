/**
 * jQuery Adjustable height no-wrap styled textarea field.
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
  $.fn.extend({
    adjustableHeightField: function(options) {
      this.each(function() {
        var self = $(this);
        $(this).css(
          {'white-space': 'pre', 'overflow': 'hidden', 'overflow-x': 'hidden'}
        ).on('input propertychange change keyup keydown mouseup mouseout', function () {
          var self = $(this),
              rows = (self.val().match(/\n/g) || []).length + 1
              scroll = self.is(':visible') && self.innerWidth() > 0 &&
                       Math.round(self.innerWidth()) < this.scrollWidth ? 1 : 0,
          self.attr('rows', rows + scroll)
              .css({'overflow-x': scroll ? 'auto' : 'hidden'});
        }).change();
      });
    },
  });
})(django && django.jQuery ? django.jQuery : jQuery); // django.jQuery also support
