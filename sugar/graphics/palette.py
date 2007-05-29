#!/usr/bin/env python

# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
from gtk import gdk, keysyms
import gobject
import pango

ALIGNMENT_BOTTOM_LEFT   = 0
ALIGNMENT_BOTTOM_RIGHT  = 1
ALIGNMENT_LEFT_BOTTOM   = 2
ALIGNMENT_LEFT_TOP      = 3
ALIGNMENT_RIGHT_BOTTOM  = 4
ALIGNMENT_RIGHT_TOP     = 5
ALIGNMENT_TOP_LEFT      = 6
ALIGNMENT_TOP_RIGHT     = 7

class Palette(gtk.Window):
    __gtype_name__ = 'SugarPalette'

    __gproperties__ = {
        'parent': (object, None, None, gobject.PARAM_READWRITE),

        'alignment': (gobject.TYPE_INT, None, None, 0, 7, ALIGNMENT_BOTTOM_LEFT,
                    gobject.PARAM_READWRITE)
    }

    _PADDING    = 1
    _WIN_BORDER = 5

    def __init__(self):

        gobject.GObject.__init__(self, type=gtk.WINDOW_POPUP)
        gtk.Window.__init__(self)

        self._palette_label = gtk.Label()
        self._palette_label.set_ellipsize(pango.ELLIPSIZE_START)
        self._palette_label.show()

        self._separator = gtk.HSeparator()
        self._separator.hide()

        self._menu_bar = gtk.MenuBar()
        self._menu_bar.set_pack_direction(gtk.PACK_DIRECTION_TTB)
        self._menu_bar.show()

        self._content = gtk.HBox()
        self._content.show()

        self._button_bar = gtk.HButtonBox()
        self._button_bar.show()

        # Set main container
        vbox = gtk.VBox(False, 0)
        vbox.pack_start(self._palette_label, False, False, self._PADDING)
        vbox.pack_start(self._separator, True, True, self._PADDING)
        vbox.pack_start(self._menu_bar, True, True, self._PADDING)
        vbox.pack_start(self._content, True, True, self._PADDING)
        vbox.pack_start(self._button_bar, True, True, self._PADDING)
        vbox.show()

        # Widget events
        self.connect('motion-notify-event', self._mouse_over_widget)
        self.connect('leave-notify-event', self._mouse_out_widget)
        self.connect('button-press-event', self._close_palette)
        self.connect('key-press-event', self._on_key_press_event)

        self.set_border_width(self._WIN_BORDER)
        self.add(vbox)
        
    def _is_mouse_out(self, window, event):
        # If we're clicking outside of the Palette
        # return True
        if (event.window != self.window or
            (tuple(self.allocation.intersect(
                   gdk.Rectangle(x=int(event.x), y=int(event.y),
                                 width=1, height=1)))) == (0, 0, 0, 0)):
            return True
        else:
            return False

    def do_set_property(self, pspec, value):

        if pspec.name == 'parent':
            self._parent_widget = value
        elif pspec.name == 'alignment':
            self._alignment = value
        else:
            raise AssertionError

    def set_position(self):

        window_axis = self._parent_widget.window.get_origin()
        parent_rectangle = self._parent_widget.get_allocation()

        palette_width, palette_height = self.get_size_request()

        # POSITIONING NOT TESTED
        if self._alignment == ALIGNMENT_BOTTOM_LEFT:
            move_x = window_axis[0] + parent_rectangle.x
            move_y = window_axis[1] + parent_rectangle.y + parent_rectangle.height

        elif self._alignment == ALIGNMENT_BOTTOM_RIGHT:
            move_x = parent_rectangle.x - palette_width
            move_y = window_axis[1] + parent_rectangle.y + parent_rectangle.height

        elif self._alignment == ALIGNMENT_LEFT_BOTTOM:
            move_x = parent_rectangle.x - palette_width
            move_y = palette_rectangle.y

        elif self._alignment == ALIGNMENT_LEFT_TOP:
            move_x = parent_rectangle.x - palette_width
            move_y = parent_rectangle.y + palette_rectangle.height

        elif self._alignment == ALIGNMENT_RIGHT_BOTTOM:
            move_x = parent_rectangle.x + parent_rectangle.width
            move_y = parent_rectangle.y

        elif self._alignment == ALIGNMENT_RIGHT_TOP:
            move_x = parent_rectangle.x + parent_rectangle.width
            move_y = parent_rectangle.y + parent_rectangle.height

        elif self._alignment == ALIGNMENT_TOP_LEFT:
            move_x = parent_rectangle.x
            move_y = parent_rectangle.y - palette_height

        elif self._alignment == ALIGNMENT_TOP_RIGHT:
            move_x = (parent_rectangle.x + parent_rectangle.width) - palette_width
            move_y = parent_rectangle.y - palette_height

        self.move(move_x, move_y)

    def _close_palette(self, widget=None, event=None):
        gtk.gdk.pointer_ungrab()
        self.hide()

    def set_primary_state(self, label, accel_path=None):
        if accel_path != None:
            item = gtk.MenuItem(label)
            item.set_accel_path(accel_path)
            self.append_menu_item(item)
            self._separator.hide()
        else:
            self._palette_label.set_text(label)
            self._separator.show()

    def append_menu_item(self, item):
        self._menu_bar.append(item)
        item.show()

    def set_content(self, widget):
        self._content.pack_start(widget, True, True, self._PADDING)
        widget.show()

    def append_button(self, button):
        button.connect('released', self._close_palette)
        self._button_bar.pack_start(button, True, True, self._PADDING)
        button.show()

    def display(self, button):
        self.show()
        self.set_position()
        self._pointer_grab()

    def _pointer_grab(self):
        gtk.gdk.pointer_grab(self.window, owner_events=False,
            event_mask=gtk.gdk.BUTTON_PRESS_MASK |
            gtk.gdk.BUTTON_RELEASE_MASK |
            gtk.gdk.ENTER_NOTIFY_MASK |
            gtk.gdk.LEAVE_NOTIFY_MASK |
            gtk.gdk.POINTER_MOTION_MASK)

        gdk.keyboard_grab(self.window, False)

    def _mouse_out_widget(self, widget, event):
        if (widget == self) and self._is_mouse_out(widget, event):
            self._pointer_grab()

    def _mouse_over_widget(self, widget, event):
        gtk.gdk.pointer_ungrab()

    def _on_key_press_event(self, window, event):
        
        # Escape or Alt+Up: Close
        # Enter, Return or Space: Select

        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()
        if (keyval == keysyms.Escape or
            ((keyval == keysyms.Up or keyval == keysyms.KP_Up) and
             state == gdk.MOD1_MASK)):
            self._close_palette()
        elif keyval == keysyms.Tab:
            self._close_palette()