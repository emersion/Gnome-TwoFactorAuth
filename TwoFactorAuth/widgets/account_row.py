# -*- coding: utf-8 -*-
"""
 Copyright © 2016 Bilal Elmoussaoui <bil.elmoussaoui@gmail.com>

 This file is part of Gnome-TwoFactorAuth.

 Gnome-TwoFactorAuth is free software: you can redistribute it and/or
 modify it under the terms of the GNU General Public License as published
 by the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 TwoFactorAuth is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with Gnome-TwoFactorAuth. If not, see <http://www.gnu.org/licenses/>.
"""
from gi import require_version
require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango
from TwoFactorAuth.models.code import Code
from TwoFactorAuth.models.settings import SettingsReader
from TwoFactorAuth.models.database import Database
from TwoFactorAuth.widgets.confirmation import ConfirmationMessage
from TwoFactorAuth.utils import get_icon
from threading import Thread
from time import sleep
import logging
from gettext import gettext as _


class RowEntryName(Gtk.Entry):

    def __init__(self, name):
        self.name = name
        self.generate()

    def generate(self):
        Gtk.Entry.__init__(self, xalign=0)
        self.set_text(self.name)
        self.set_width_chars(25)
        self.set_max_width_chars(25)
        self.hide()

    def toggle(self, visible):
        self.set_visible(visible)
        self.set_no_show_all(not visible)

    def is_visible(self):
        return self.get_visible()

    def hide(self):
        self.toggle(False)

    def show(self):
        self.toggle(True)

    def focus(self):
        self.grab_focus_without_selecting()

class AccountRow(Thread, Gtk.ListBoxRow):
    counter_max = 30
    counter = 30
    timer = 0
    code = None
    code_generated = True
    alive = True

    def __init__(self, parent, window, app):
        Thread.__init__(self)
        Gtk.ListBoxRow.__init__(self)
        # Read default values
        cfg = SettingsReader()
        self.counter_max = cfg.read("refresh-time", "preferences")
        self.counter = self.counter_max
        self.window = window
        self.parent = parent
        self.id = app[0]
        self.name = app[1]
        self.secret_code = Database.fetch_secret_code(app[2])
        if self.secret_code:
            self.code = Code(self.secret_code)
        else:
            self.code_generated = False
            logging.error(
                "Could not read the secret code from, the keyring keys were reset manually")
        self.logo = app[3]
        # Create needed widgets
        self.code_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.revealer = Gtk.Revealer()
        self.checkbox = Gtk.CheckButton()
        self.application_name = Gtk.Label(xalign=0)
        self.code_label = Gtk.Label(xalign=0)
        self.timer_label = Gtk.Label(xalign=0)
        # Create the list row
        self.create_row()
        self.start()
        self.window.connect("key-press-event", self.__on_key_press)

    def get_id(self):
        """
            Get the application id
            :return: (int): row id
        """
        return self.id

    def get_name(self):
        """
            Get the application name
            :return: (str): application name
        """
        return self.name

    def get_code(self):
        return self.code

    def get_code_label(self):
        return self.code_label

    def get_checkbox(self):
        """
            Get ListBowRow's checkbox
            :return: (Gtk.Checkbox)
        """
        return self.checkbox

    def get_code_box(self):
        """
            Get code's box
            :return: (Gtk.Box)
        """
        return self.code_box

    def toggle_code_box(self):
        """
            Toggle code box
        """
        self.revealer.set_reveal_child(not self.revealer.get_reveal_child())

    def kill(self):
        """
            Kill the row thread once it's removed
        """
        self.alive = False

    def copy_code(self, *args):
        """
            Copy code shows the code box for a while (10s by default)
        """
        self.timer = 0
        code = self.get_code().get_secret_code()
        try:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.clear()
            clipboard.set_text(code, len(code))
            logging.debug("Secret code copied to clipboard")
        except Exception as e:
            logging.error(str(e))
        self.revealer.set_reveal_child(True)
        GLib.timeout_add_seconds(1, self.update_timer)

    def update_timer(self, *args):
        """
            Update timer
        """
        self.timer += 1
        if self.timer > 10:
            self.revealer.set_reveal_child(False)
        return self.timer <= 10

    def create_row(self):
        """
            Create ListBoxRow
        """
        self.get_style_context().add_class("application-list-row")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        h_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(h_box, True, True, 0)
        box.pack_start(self.revealer, True, True, 0)

        # Checkbox
        self.checkbox.set_visible(False)
        self.checkbox.set_no_show_all(True)
        self.checkbox.connect("toggled", self.parent.select_account)
        h_box.pack_start(self.checkbox, False, True, 6)

        # account logo
        auth_icon = get_icon(self.logo)
        auth_logo = Gtk.Image(xalign=0)
        auth_logo.set_from_pixbuf(auth_icon)
        h_box.pack_start(auth_logo, False, True, 6)

        # Account name entry
        name_entry_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.name_entry = RowEntryName(self.name)
        name_entry_box.pack_start(self.name_entry, False, False, 6)
        h_box.pack_start(name_entry_box, False, False, 0)
        name_entry_box.set_visible(False)

        # accout name
        name_event = Gtk.EventBox()
        self.application_name .get_style_context().add_class("application-name")
        self.application_name.set_ellipsize(Pango.EllipsizeMode.END)
        self.application_name.props.tooltip_text = self.name
        self.application_name .set_text(self.name)
        name_event.connect("button-press-event", self.toggle_code)
        name_event.add(self.application_name)
        h_box.pack_start(name_event, False, True, 6)

        # Remove button
        self.actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        remove_event = Gtk.EventBox()
        remove_button = Gtk.Image(xalign=0)
        remove_button.set_from_icon_name("user-trash-symbolic",
                                         Gtk.IconSize.SMALL_TOOLBAR)
        remove_button.set_tooltip_text(_("Remove the account"))
        remove_event.add(remove_button)
        remove_event.connect("button-press-event", self.remove)
        self.actions_box.pack_end(remove_event, False, False, 6)

        # Copy button
        copy_event = Gtk.EventBox()
        copy_button = Gtk.Image(xalign=0)
        copy_button.set_from_icon_name(
            "edit-copy-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        copy_button.set_tooltip_text(_("Copy the generated code"))
        copy_event.connect("button-press-event", self.copy_code)
        copy_event.add(copy_button)
        self.actions_box.pack_end(copy_event, False, False, 6)

        # Edit button
        edit_event = Gtk.EventBox()
        self.edit_button = Gtk.Image(xalign=0)
        self.edit_button.set_from_icon_name("document-edit-symbolic",
                                        Gtk.IconSize.SMALL_TOOLBAR)
        self.edit_button.set_tooltip_text(_("Edit the account"))
        edit_event.add(self.edit_button)
        edit_event.connect("button-press-event", self.edit)
        self.actions_box.pack_end(edit_event, False, False, 6)

        # Apply button
        apply_event = Gtk.EventBox()
        self.apply_button = Gtk.Image(xalign=0)
        self.apply_button.set_from_icon_name("emblem-ok-symbolic",
                                        Gtk.IconSize.SMALL_TOOLBAR)
        self.apply_button.set_tooltip_text(_("Save the new account name"))
        apply_event.add(self.apply_button)
        apply_event.connect("button-press-event", self.apply_edit_name)
        self.actions_box.pack_end(apply_event, False, False, 6)
        h_box.pack_end(self.actions_box, False, False, 0)
        self.toggle_action_box(True)
        self.toggle_edit_mode(False)

        self.timer_label.set_label(_("Expires in %s seconds") % self.counter)
        self.timer_label.get_style_context().add_class("account-timer")
        self.code_label.get_style_context().add_class("account-secret-code")
        if self.code_generated:
            self.update_code(self.code_label)
        else:
            self.code_label.set_text(_("Error during the generation of code"))

        self.code_box.pack_end(self.timer_label, False, True, 6)
        self.code_box.pack_start(self.code_label, False, True, 6)
        self.revealer.add(self.code_box)
        self.revealer.set_reveal_child(False)
        self.add(box)

    def get_counter(self):
        return self.counter

    def toggle_code(self, *args):
        self.toggle_code_box()

    def toggle_action_box(self, visible):
        self.actions_box.set_visible(visible)
        self.actions_box.set_no_show_all(not visible)

    def run(self):
        while self.code_generated and self.window.app.alive and self.alive:
            self.counter -= 1
            if self.counter == 0:
                self.counter = self.counter_max
                self.regenerate_code()
                if self.timer != 0:
                    self.timer = 0
            self.update_timer_label()
            self.changed()
            sleep(1)

    def regenerate_code(self):
        label = self.code_label
        if label:
            self.code.update()
            self.update_code(label)

    def update_code(self, label):
        try:
            code = self.code.get_secret_code()
            if code:
                label.set_text(code)
            else:
                raise TypeError
        except TypeError as e:
            logging.error("Couldn't generate the secret code : %s" % str(e))
            label.set_text(_("Couldn't generate the secret code"))
            self.code_generated = False

    def toggle_edit_mode(self, visible):
        if visible:
            self.name_entry.show()
            self.name_entry.set_text(self.get_name())
            self.name_entry.focus()
        else:
            self.name_entry.hide()
        self.application_name.set_visible(not visible)
        self.application_name.set_no_show_all(visible)
        self.apply_button.set_visible(visible)
        self.apply_button.set_no_show_all(not visible)
        self.edit_button.get_parent().set_visible(not visible)
        self.edit_button.get_parent().set_no_show_all(visible)


    def __on_key_press(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval).lower()
        if not self.window.is_locked():
            if self.parent.get_selected_row_id() == self.get_id():
                is_search_bar = self.window.search_bar.is_visible()
                is_editing_name = self.name_entry.is_visible()
                if keyname == "delete" and not is_search_bar and not is_editing_name:
                    self.remove()
                    return True

                if keyname == "escape":
                    if is_editing_name:
                        self.toggle_edit_mode(False)
                        return True

                if keyname == "return":
                    if is_editing_name:
                        self.apply_edit_name()
                    else:
                        self.toggle_code_box()
                    return True

                if event.state & Gdk.ModifierType.CONTROL_MASK:
                    if keyname == 'c':
                        self.copy_code()
                        return True
        return False

    def edit(self, *args):
        is_visible = self.name_entry.is_visible()
        self.toggle_edit_mode(not is_visible)
        self.parent.select_row(self)

    def apply_edit_name(self, *args):
        new_name = self.name_entry.get_text()
        self.application_name.set_text(new_name)
        self.window.app.db.update_name_by_id(self.get_id(), new_name)
        self.name = new_name
        self.toggle_edit_mode(False)

    def remove(self, *args):
        """
            Remove an account
        """
        message = _('Do you really want to remove "%s"?' % self.get_name())
        confirmation = ConfirmationMessage(self.window, message)
        confirmation.show()
        if confirmation.get_confirmation():
            self.kill()
            self.window.accounts_list.remove(self)
            self.window.app.db.remove_by_id(self.get_id())
        confirmation.destroy()
        self.window.refresh_window()

    def update_timer_label(self):
        self.timer_label.set_label(_("Expires in %s seconds") % self.counter)
