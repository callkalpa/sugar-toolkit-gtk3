# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging

import gtk
import gobject
import time
import hippo

from sugar.graphics import palettegroup
from sugar.graphics import animator
from sugar.graphics import units
from sugar.graphics import style
from sugar import _sugarext

_BOTTOM_LEFT  = 0
_BOTTOM_RIGHT = 1
_LEFT_BOTTOM  = 2
_LEFT_TOP     = 3
_RIGHT_BOTTOM = 4
_RIGHT_TOP    = 5
_TOP_LEFT     = 6
_TOP_RIGHT    = 7

class Palette(gobject.GObject):
    DEFAULT   = 0
    AT_CURSOR = 1
    AROUND    = 2
    BOTTOM    = 3
    LEFT      = 4
    RIGHT     = 5
    TOP       = 6

    __gtype_name__ = 'SugarPalette'

    __gproperties__ = {
        'invoker'    : (object, None, None,
                        gobject.PARAM_READWRITE),
        'position'   : (gobject.TYPE_INT, None, None, 0, 5,
                        0, gobject.PARAM_READWRITE)
    }

    __gsignals__ = {
        'popup' :   (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, ([])),
        'popdown' : (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, ([]))
    }

    def __init__(self, label, accel_path=None):
        gobject.GObject.__init__(self)

        self._invoker = None
        self._group_id = None
        self._up = False
        self._position = self.DEFAULT
        self._palette_popup_sid = None

        self._popup_anim = animator.Animator(0.3, 10)
        self._popup_anim.add(_PopupAnimation(self))

        self._secondary_anim = animator.Animator(1.0, 10)
        self._secondary_anim.add(_SecondaryAnimation(self))

        self._popdown_anim = animator.Animator(0.6, 10)
        self._popdown_anim.add(_PopdownAnimation(self))

        self._menu = _sugarext.Menu()
        self._menu.set_min_width(units.grid_to_pixels(1))

        self._primary = _PrimaryMenuItem(label, accel_path)
        self._menu.append(self._primary)
        self._primary.show()

        self._separator = gtk.SeparatorMenuItem()
        self._menu.append(self._separator)

        self._content = _ContentMenuItem()
        self._menu.append(self._content)

        self._button_bar = _ButtonBarMenuItem()
        self._menu.append(self._button_bar)

        self._menu.connect('enter-notify-event',
                           self._enter_notify_event_cb)
        self._menu.connect('leave-notify-event',
                           self._leave_notify_event_cb)

    def is_up(self):
        return self._up

    def set_primary_text(self, label, accel_path=None):
        self._primary.set_label(label, accel_path)

    def append_menu_item(self, item):
        self._separator.show()
        self._menu.insert(item, len(self._menu.get_children()) - 2)

    def insert_menu_item(self, item, index=-1):
        self._separator.show()
        if index < 0:
            self._menu.insert(item, len(self._menu.get_children()) - 2)
        else:
            self._menu.insert(item, index + 2)

    def remove_menu_item(self, index):
        if index > len(self._menu.get_children()) - 4:
            raise ValueError('index %i out of range' % index)
        self._menu.remove(self._menu.get_children()[index + 2])
        if len(self._menu.get_children()) == 0:
            self._separator.hide()

    def menu_item_count(self):
        return len(self._menu.get_children()) - 4
        
    def set_content(self, widget):
        self._content.set_widget(widget)
        self._content.show()

    def append_button(self, button):
        self._button_bar.append_button(button)
        self._button_bar.show()

    def set_group_id(self, group_id):
        if self._group_id:
            group = palettegroup.get_group(self._group_id)
            group.remove(self)
        if group_id:
            group = palettegroup.get_group(group_id)
            group.add(self)

    def do_set_property(self, pspec, value):
        if pspec.name == 'invoker':
            self._invoker = value
            self._invoker.connect('mouse-enter', self._invoker_mouse_enter_cb)
            self._invoker.connect('mouse-leave', self._invoker_mouse_leave_cb)
            self._invoker.connect('focus-out', self._invoker_focus_out_cb)
        elif pspec.name == 'position':
            self._position = value
        else:
            raise AssertionError

    def do_get_property(self, pspec):
        if pspec.name == 'invoker':
            return self._invoker
        elif pspec.name == 'position':
            return self._position
        else:
            raise AssertionError

    def _in_screen(self, x, y):
        [width, height] = self._menu.size_request()
        screen_area = self._invoker.get_screen_area()

        return x >= screen_area.x and \
               y >= screen_area.y and \
               x + width <= screen_area.width and \
               y + height <= screen_area.height

    def _get_position(self, palette_halign, palette_valign,
                      invoker_halign, invoker_valign, inv_rect=None):
        if inv_rect == None:
            inv_rect = self._invoker.get_rect()

        palette_width, palette_height = self._menu.size_request()

        x = inv_rect.x + inv_rect.width * invoker_halign + \
            palette_width * palette_halign

        y = inv_rect.y + inv_rect.height * invoker_valign + \
            palette_height * palette_valign

        return int(x), int(y)

    def _get_left_position(self, inv_rect=None):
        x, y = self._get_position(-1.0, 0.0, 0.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, -1.0, 0.0, 1.0, inv_rect)
        return x, y

    def _get_right_position(self, inv_rect=None):
        x, y = self._get_position(0.0, 0.0, 1.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(0.0, -1.0, 1.0, 1.0, inv_rect)
        return x, y

    def _get_top_position(self, inv_rect=None):
        x, y = self._get_position(0.0, -1.0, 0.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, -1.0, 1.0, 0.0, inv_rect)
        return x, y

    def _get_bottom_position(self, inv_rect=None):
        x, y = self._get_position(0.0, 0.0, 0.0, 1.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, 0.0, 1.0, 1.0, inv_rect)
        return x, y

    def _get_around_position(self, inv_rect=None):
        x, y = self._get_bottom_position(inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_right_position(inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_top_position(inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_left_position(inv_rect)

        return x, y

    def _get_at_cursor_position(self, inv_rect=None):
        x, y = self._get_position(0.0, 0.0, 1.0, 1.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(0.0, -1.0, 1.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, -1.0, 0.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, 0.0, 0.0, 1.0, inv_rect)

        return x, y

    def _show(self):
        if self._up:
            return

        x = y = 0

        if self._position == self.DEFAULT:
            position = self._invoker.get_default_position()
        else:
            position = self._position

        if position == self.AT_CURSOR:
            display = gtk.gdk.display_get_default()
            screen, x, y, mask = display.get_pointer()
            dist = style.PALETTE_CURSOR_DISTANCE

            rect = gtk.gdk.Rectangle(x - dist, y - dist, dist * 2, dist * 2)
            x, y = self._get_at_cursor_position(rect)
        elif position == self.AROUND:
            x, y = self._get_around_position()
        elif position == self.BOTTOM:
            x, y = self._get_bottom_position()
        elif position == self.LEFT:
            x, y = self._get_left_position()
        elif position == self.RIGHT:
            x, y = self._get_right_position()
        elif position == self.TOP:
            x, y = self._get_top_position()

        self._invoker.connect_to_parent()

        self._palette_popup_sid = _palette_observer.connect('popup',
                    self._palette_observer_popup_cb)
        self._menu.popup(x, y)

        self._up = True
        _palette_observer.emit('popup', self)
        self.emit('popup')

    def _hide(self):
        if not self._palette_popup_sid is None:
            _palette_observer.disconnect(self._palette_popup_sid)
            self._palette_popup_sid = None
        self._menu.popdown()

        self._up = False
        self.emit('popdown')

    def popup(self):
        self._popdown_anim.stop()
        self._popup_anim.start()
        self._secondary_anim.start()

    def popdown(self, inmediate=False):
        self._secondary_anim.stop()
        self._popup_anim.stop()

        if not inmediate:
            self._popdown_anim.start()
        else:
            self._hide()

    def _invoker_mouse_enter_cb(self, invoker):
        self.popup()

    def _invoker_mouse_leave_cb(self, invoker):
        self.popdown()

    def _invoker_focus_out_cb(self, invoker):
        self._hide()

    def _enter_notify_event_cb(self, widget, event):
        if event.detail == gtk.gdk.NOTIFY_NONLINEAR:
            self._popdown_anim.stop()
            self._secondary_anim.start()

    def _leave_notify_event_cb(self, widget, event):
        if event.detail == gtk.gdk.NOTIFY_NONLINEAR:
            self.popdown()

    def _palette_observer_popup_cb(self, observer, palette):
        if self != palette:
            self._hide()

class _PrimaryMenuItem(gtk.MenuItem):
    def __init__(self, label, accel_path):
        gtk.MenuItem.__init__(self)
        self.set_border_width(units.points_to_pixels(1))
        self._set_label(label, accel_path)

    def set_label(self, label, accel_path):
        self.remove(self._label)
        self._set_label(label, accel_path)

    def _set_label(self, label, accel_path):
        self._label = gtk.AccelLabel(label)
        self._label.set_accel_widget(self)

        if accel_path:
            self.set_accel_path(accel_path)
            self._label.set_alignment(0.0, 0.5)

        self.add(self._label)
        self._label.show()
    
class _ContentMenuItem(gtk.MenuItem):
    def __init__(self):
        gtk.MenuItem.__init__(self)

    def set_widget(self, widget):
        if self.child:
            self.remove(self.child)
        self.add(widget)

    def is_empty(self):
        return self.child is None or not self.child.props.visible

class _ButtonBarMenuItem(gtk.MenuItem):
    def __init__(self):
        gtk.MenuItem.__init__(self)

        self._hbar = gtk.HButtonBox()
        self.add(self._hbar)
        self._hbar.show()

    def append_button(self, button):
        self._hbar.pack_start(button)

    def is_empty(self):
        return len(self._hbar.get_children()) == 0

class _PopupAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette._primary.show()
            for menu_item in self._palette._menu.get_children()[1:]:
                menu_item.hide()
            self._palette._show()

class _SecondaryAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            middle_menu_items = self._palette._menu.get_children()
            middle_menu_items = middle_menu_items[2:len(middle_menu_items) - 2]
            if middle_menu_items or \
                    not self._palette._content.is_empty() or \
                    not self._palette._button_bar.is_empty():
                self._palette._separator.show()

            for menu_item in middle_menu_items:
                menu_item.show()

            if not self._palette._content.is_empty():
                self._palette._content.show()

            if not self._palette._button_bar.is_empty():
                self._palette._button_bar.show()

            self._palette._show()

class _PopdownAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette._hide()

class Invoker(gobject.GObject):
    __gtype_name__ = 'SugarPaletteInvoker'

    __gsignals__ = {
        'mouse-enter': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'mouse-leave': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'focus-out':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

    def get_default_position(self):
        return Palette.AROUND

    def get_screen_area(self):
        width = gtk.gdk.screen_width()
        height = gtk.gdk.screen_height()
        return gtk.gdk.Rectangle(0, 0, width, height)

    def connect_to_parent(self):
        window = self.get_toplevel()
        window.connect('focus-out-event', self._window_focus_out_event_cb)

    def _window_focus_out_event_cb(self, widget, event):
        self.emit('focus-out')

class WidgetInvoker(Invoker):
    def __init__(self, widget):
        Invoker.__init__(self)
        self._widget = widget

        widget.connect('enter-notify-event', self._enter_notify_event_cb)
        widget.connect('leave-notify-event', self._leave_notify_event_cb)

    def get_rect(self):
        win_x, win_y = self._widget.window.get_origin()
        rectangle = self._widget.get_allocation()

        x = win_x + rectangle.x
        y = win_y + rectangle.y
        width = rectangle.width
        height = rectangle.height

        return gtk.gdk.Rectangle(x, y, width, height)

    def _enter_notify_event_cb(self, widget, event):
        self.emit('mouse-enter')

    def _leave_notify_event_cb(self, widget, event):
        self.emit('mouse-leave')

    def get_toplevel(self):
        return self._widget.get_toplevel()

class CanvasInvoker(Invoker):
    def __init__(self, item):
        Invoker.__init__(self)
        self._item = item

        item.connect('motion-notify-event',
                     self._motion_notify_event_cb)

    def get_default_position(self):
        return Palette.AT_CURSOR

    def get_rect(self):
        context = self._item.get_context()
        if context:
            x, y = context.translate_to_screen(self._item)

        width, height = self._item.get_allocation()

        return gtk.gdk.Rectangle(x, y, width, height)

    def _motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self.emit('mouse-enter')
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.emit('mouse-leave')

        return False

    def get_toplevel(self):
        return hippo.get_canvas_for_item(self._item).get_toplevel()

class _PaletteObserver(gobject.GObject):
    __gtype_name__ = 'SugarPaletteObserver'

    __gsignals__ = {
        'popup': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([object]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

_palette_observer = _PaletteObserver()
