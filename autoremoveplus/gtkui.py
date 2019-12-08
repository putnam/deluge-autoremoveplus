#
# gtkui.py
#
# Copyright (C) 2014-2016 Omar Alvarez <osurfer3@hotmail.com>
# Copyright (C) 2011 Jamie Lennox <jamielennox@gmail.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

import gtk

from deluge.log import LOG as log
from deluge.ui.client import client
from deluge.plugins.pluginbase import GtkPluginBase
import deluge.component as component
# import deluge.common

from common import get_resource


class GtkUI(GtkPluginBase):

    def enable(self):
        log.debug("Enabling AutoRemovePlus...")
        self.glade = gtk.glade.XML(get_resource("config.glade"))
        component.get("Preferences").add_page(
            "AutoRemovePlus",
            self.glade.get_widget("prefs_box")
        )
        component.get("PluginManager").register_hook(
            "on_apply_prefs",
            self.on_apply_prefs
        )
        component.get("PluginManager").register_hook(
            "on_show_prefs",
            self.on_show_prefs
        )

        # Create and fill remove rule list
        self.rules = gtk.ListStore(str, str)
        client.autoremoveplus.get_remove_rules().addCallback(self.cb_get_rules)

        # Fill list with logical functions
        self.sel_func_store = gtk.ListStore(str)
        self.sel_func_store.append(["and"])
        self.sel_func_store.append(["or"])

        # Buttons to add/delete rules
        self._new_rule = self.glade.get_widget("new_rule")
        self._new_rule.connect("clicked", self._do_new_rule)
        self._delete_rule = self.glade.get_widget("delete_rule")
        self._delete_rule.connect("clicked", self._do_delete_rule)

        # Table to keep all rules
        self._blk_rules = self.glade.get_widget("blk_rules")
        self._view = self._build_view_rules()
        window_rules = gtk.ScrolledWindow()
        window_rules.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        window_rules.set_shadow_type(gtk.SHADOW_IN)
        window_rules.add(self._view)
        self._blk_rules.add(window_rules)
        self._blk_rules.show_all()

        cell = gtk.CellRendererText()

        cbo_remove = self.glade.get_widget("cbo_remove")
        cbo_remove.pack_start(cell, True)
        cbo_remove.add_attribute(cell, 'text', 1)
        cbo_remove.set_model(self.rules)

        cbo_remove1 = self.glade.get_widget("cbo_remove1")
        cbo_remove1.pack_start(cell, True)
        cbo_remove1.add_attribute(cell, 'text', 1)
        cbo_remove1.set_model(self.rules)

        cbo_sel_func = self.glade.get_widget("cbo_sel_func")
        cbo_sel_func.set_model(self.sel_func_store)
        cbo_sel_func.set_active(0)
        self.glade.get_widget("dummy").set_model(self.sel_func_store)

        self._new_tracker = self.glade.get_widget("new_tracker")
        self._new_tracker.connect("clicked", self._do_new_tracker)
        self._delete_tracker = self.glade.get_widget("delete_tracker")
        self._delete_tracker.connect("clicked", self._do_delete_tracker)

        self._blk_trackers = self.glade.get_widget("blk_trackers")
        self._view_trackers = self._build_view_trackers()
        window = gtk.ScrolledWindow()
        window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        window.set_shadow_type(gtk.SHADOW_IN)
        window.add(self._view_trackers)
        self._blk_trackers.add(window)
        self._blk_trackers.show_all()

        self.glade.get_widget("chk_remove").connect(
            "toggled",
            self.on_click_remove
        )

        self.glade.get_widget("chk_enabled").connect(
            "toggled",
            self.on_click_enabled
        )

        self.glade.get_widget("chk_rule_1").connect(
            "toggled",
            self.on_click_chk_rule_1
        )

        self.glade.get_widget("chk_rule_2").connect(
            "toggled",
            self.on_click_chk_rule_2
        )

        def on_menu_show(menu, settings):
            (menu_item, toggled) = settings
            def set_ignored(ignored):
                # set_active will raise the 'toggled'/'activated' signals
                # so block it to not reset the value
                menu_item.handler_block(toggled)
                menu_item.set_active(False not in ignored)
                menu_item.handler_unblock(toggled)

            client.autoremoveplus.get_ignore([t for t in component.get("TorrentView").get_selected_torrents() ]).addCallback(set_ignored)

        def on_menu_toggled(menu):
            client.autoremoveplus.set_ignore(component.get("TorrentView").get_selected_torrents(), menu.get_active())

        self.menu = gtk.CheckMenuItem(_("AutoRemovePlus Exempt"))
        self.menu.show()

        toggled = self.menu.connect('toggled', on_menu_toggled)

        torrentmenu = component.get("MenuBar").torrentmenu
        self.show_sig = torrentmenu.connect('show', on_menu_show, (self.menu, toggled))
        self.realize_sig = torrentmenu.connect('realize', on_menu_show, (self.menu, toggled))
        torrentmenu.append(self.menu)

        self.on_show_prefs()

    def disable(self):
        component.get("Preferences").remove_page("AutoRemovePlus")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)

        torrentmenu = component.get("MenuBar").torrentmenu
        torrentmenu.remove(self.menu)
        torrentmenu.disconnect(self.show_sig)
        torrentmenu.disconnect(self.realize_sig)

        del self.rules
        del self.sel_func_store
        del self.menu
        del self.show_sig
        del self.realize_sig

    def on_click_remove(self, check):
        checked = check.get_active()
        self.glade.get_widget("chk_remove_data").set_sensitive(checked)

    def disable_all_widgets(self, checked):
        self.glade.get_widget("hbox4").set_sensitive(checked)
        self.glade.get_widget("hbox2").set_sensitive(checked)
        self.glade.get_widget("hbox6").set_sensitive(checked)
        self.glade.get_widget("hbox1").set_sensitive(checked)
        self.glade.get_widget("hbox5").set_sensitive(checked)
        self.glade.get_widget("vbox2").set_sensitive(checked)
        self.glade.get_widget("chk_count").set_sensitive(checked)
        self.glade.get_widget("chk_remove").set_sensitive(checked)
        if not checked:
            self.glade.get_widget("chk_remove_data").set_sensitive(checked)
        else:
            self.glade.get_widget("chk_remove_data").set_sensitive(
                self.glade.get_widget("chk_remove").get_active()
            )

    def on_click_enabled(self, check):
        self.disable_all_widgets(check.get_active())

    def disable_rule(self, checked, rule):
        self.glade.get_widget("hb_rule_%i" % rule).set_sensitive(checked)

    def on_click_chk_rule_1(self, check):
        self.disable_rule(check.get_active(), 1)

    def on_click_chk_rule_2(self, check):
        self.disable_rule(check.get_active(), 2)

    def _do_new_rule(self,button):
        new_row = self.lstore_rules.append(["Tracker", "New Tracker", "and", "Ratio", 0.0])
        #self._view.set_cursor("3", start_editing=True)
        path = self.lstore_rules.get_path(new_row)
        self._view.set_cursor(path, focus_column=self._view.get_column(1), start_editing=True)

    def _do_delete_rule(self,button):
        selection = self._view.get_selection()
        model, paths = selection.get_selected_rows()

        for path in paths:
            iter = model.get_iter(path)
            model.remove(iter)

    def _do_new_tracker(self,button):
        new_row = self.lstore.append(["Tracker","New Tracker"])
        #self._view.set_cursor("3", start_editing=True)
        path = self.lstore.get_path(new_row)
        self._view_trackers.set_cursor(path, focus_column=self._view_trackers.get_column(1), start_editing=True)

    def _do_delete_tracker(self,button):
        selection = self._view_trackers.get_selection()
        model, paths = selection.get_selected_rows()

        for path in paths:
            iter = model.get_iter(path)
            model.remove(iter)

    def on_apply_prefs(self):
        log.debug("applying prefs for AutoRemovePlus")
        # log.debug("Min: %f" % (self.glade.get_widget("spn_min").get_value()))
        c = self.glade.get_widget("cbo_remove")
        c1 = self.glade.get_widget("cbo_remove1")

        trackers = []
        labels = []

        for row in self._view_trackers.get_model():
            if row[0] == "Tracker":
                trackers.append(row[1])
            else:
                labels.append(row[1])

        tracker_rules = {}
        label_rules = {}

        for row in self._view.get_model():
            # Look for rule key for config
            for row_r in list(self.rules):
                if row_r[1] == row[3]:
                    func = row_r[0]
                    break

            rule = [row[2], func, row[4]]

            # Insert rule in correct list tracker/label
            if row[0] == "Tracker":
                tracker_rules.setdefault(row[1], []).append(rule)
            else:
                label_rules.setdefault(row[1], []).append(rule)

        config = {
            'max_seeds': self.glade.get_widget('spn_seeds').get_value_as_int(),
            'filter': c.get_model()[c.get_active_iter()][0],
            'count_exempt': self.glade.get_widget('chk_count').get_active(),
            'remove_data': self.glade.get_widget('chk_remove_data').get_active(),
            'trackers': trackers,
            'labels': labels,
            'min': self.glade.get_widget("spn_min").get_value(),
            'interval': self.glade.get_widget("spn_interval").get_value(),
            'sel_func': self.glade.get_widget("cbo_sel_func").get_active_text(),
            'filter2': c1.get_model()[c1.get_active_iter()][0],
            'min2': self.glade.get_widget("spn_min1").get_value(),
            'hdd_space': self.glade.get_widget("spn_min2").get_value(),
            'remove': self.glade.get_widget('chk_remove').get_active(),
            'enabled': self.glade.get_widget('chk_enabled').get_active(),
            'tracker_rules': tracker_rules,
            'label_rules': label_rules,
            'rule_1_enabled': self.glade.get_widget('chk_rule_1').get_active(),
            'rule_2_enabled': self.glade.get_widget('chk_rule_2').get_active()
        }

        client.autoremoveplus.set_config(config)

    def on_show_prefs(self):
        client.autoremoveplus.get_config().addCallback(self.cb_get_config)

    def cb_get_rules(self, rules):
        self.rules.clear()

        for k, v in rules.items():
            self.rules.append((k, v))

    def cb_get_config(self, config):
        self.glade.get_widget('spn_seeds').set_value(config['max_seeds'])
        self.glade.get_widget('spn_min').set_value(config['min'])
        self.glade.get_widget('spn_min1').set_value(config['min2'])
        self.glade.get_widget('spn_min2').set_value(config['hdd_space'])
        self.glade.get_widget('chk_count').set_active(config['count_exempt'])
        self.glade.get_widget('chk_remove_data').set_active(config['remove_data'])
        self.glade.get_widget('spn_interval').set_value(config['interval'])
        self.glade.get_widget('chk_remove').set_active(config['remove'])
        self.glade.get_widget('chk_enabled').set_active(config['enabled'])
        self.glade.get_widget('chk_rule_1').set_active(config['rule_1_enabled'])
        self.glade.get_widget('chk_rule_2').set_active(config['rule_2_enabled'])
        self.disable_all_widgets(config['enabled'])
        self.disable_rule(config['rule_1_enabled'], 1)
        self.disable_rule(config['rule_2_enabled'], 2)


        self.lstore_rules.clear()
        tracker_rules = config['tracker_rules']
        for tracker in tracker_rules:
            for rule in tracker_rules[tracker]:
                for row in list(self.rules):
                    if row[0] == rule[1]:
                        rule_text = row[1]

                self.lstore_rules.append(['Tracker', tracker, rule[0], rule_text, rule[2]])

        label_rules = config['label_rules']
        for label in label_rules:
            for rule in label_rules[label]:
                for row in list(self.rules):
                    if row[0] == rule[1]:
                        rule_text = row[1]

                self.lstore_rules.append(['Label', label, rule[0], rule_text, rule[2]])

        self.lstore.clear()
        trackers = config['trackers']
        for tracker in trackers:
            self.lstore.append(["Tracker", tracker])

        labels = config['labels']
        for label in labels:
            self.lstore.append(["Label", label])

        selected = config['filter']

        for i, row in enumerate(self.rules):
            if row[0] == selected:
                self.glade.get_widget("cbo_remove").set_active(i)
                break
        else:
            self.glade.get_widget("cbo_remove").set_active(0)


        selected = config['filter2']

        for i, row in enumerate(self.rules):
            if row[0] == selected:
                self.glade.get_widget("cbo_remove1").set_active(i)
                break
        else:
            self.glade.get_widget("cbo_remove1").set_active(0)

        selected = config['sel_func']

        for i, row in enumerate(self.sel_func_store):

            if row[0] == selected:
                self.glade.get_widget("cbo_sel_func").set_active(i)
                break
        else:
            self.glade.get_widget("cbo_sel_func").set_active(0)

    def _build_view_rules(self):
        self.lstore_rules = gtk.ListStore(str, str, str, str, float)
        view = gtk.TreeView(model=self.lstore_rules)

        # Create field to set the type of rule tracker/label
        liststore_field_type = gtk.ListStore(str)
        for item in ["Tracker", "Label"]:
            liststore_field_type.append([item])
        crc = gtk.CellRendererCombo()
        crc.set_property("editable", True)
        crc.set_property("model", liststore_field_type)
        crc.set_property("text-column", 0)
        crc.set_property("has-entry", False)
        crc.connect("edited", self._on_combo_type_changed)
        # crc.set_active(0)
        colc = gtk.TreeViewColumn(_("Type"), crc, text=0)
        view.append_column(colc)

        # Create text field for label or tracker names
        crt = gtk.CellRendererText()
        crt.set_property("editable", True)
        crt.connect("edited", self._on_name_changed)
        colt = gtk.TreeViewColumn(_("Name"), crt, text=1)
        view.append_column(colt)

        # Create field to set the type of selection and/or
        liststore_field_logic = self.sel_func_store
        crl = gtk.CellRendererCombo()
        crl.set_property("editable", True)
        crl.set_property("model", liststore_field_logic)
        crl.set_property("text-column", 0)
        crl.set_property("has-entry", False)
        crl.connect("edited", self._on_combo_logic_changed)
        #crl.set_active(0) #TODO
        coll = gtk.TreeViewColumn(_("Operator"), crl, text=2)
        view.append_column(coll)

        # Create field for remove rule selection
        liststore_field_rules = self.rules
        crrr = gtk.CellRendererCombo()
        crrr.set_property("editable", True)
        crrr.set_property("model", liststore_field_rules)
        crrr.set_property("text-column", 1)
        crrr.set_property("has-entry", False)
        crrr.connect("edited", self._on_combo_rules_changed)
        colrr = gtk.TreeViewColumn(_("Remove Rule"), crrr, text=3)
        view.append_column(colrr)

        # Spin button for minimum value
        crm = gtk.CellRendererSpin()
        crm.set_property("editable", True)
        crm.set_property("digits", 3)
        crm.set_property("adjustment", gtk.Adjustment(0, 0, 10000.0, 0.5, 10,0))
        crm.connect("edited", self._on_spin_min_changed)
        colm = gtk.TreeViewColumn(_("Minimum"), crm, text=4)
        view.append_column(colm)

        return view

    def _on_combo_type_changed(self, widget, path, text):
        self.lstore_rules[path][0] = text

    def _on_name_changed(self, widget, path, text):
        self.lstore_rules[path][1] = text

    def _on_combo_logic_changed(self, widget, path, text):
        self.lstore_rules[path][2] = text

    def _on_combo_rules_changed(self, widget, path, text):
        self.lstore_rules[path][3] = text

    def _on_spin_min_changed(self, widget, path, value):
        self.lstore_rules[path][4] = float(value)

    def _build_view_trackers(self):
        self.lstore = gtk.ListStore(str, str)
        view = gtk.TreeView(model=self.lstore)

        # Create field to set the type of exemption
        liststore_field = gtk.ListStore(str)
        for item in ["Tracker", "Label"]:
            liststore_field.append([item])
        crc = gtk.CellRendererCombo()
        crc.set_property("editable", True)
        crc.set_property("model", liststore_field)
        crc.set_property("text-column", 0)
        crc.set_property("has-entry", False)
        crc.connect("edited", self._on_combo_changed)
        # crc.set_active(0)
        colc = gtk.TreeViewColumn(_("Type"), crc, text=0)
        view.append_column(colc)

        # Create text field for label or tracker names
        crt = gtk.CellRendererText()
        crt.set_property("editable", True)
        crt.connect("edited", self._text_edited)
        colt = gtk.TreeViewColumn(_("Name"), crt, text=1)
        view.append_column(colt)

        return view

    def _on_combo_changed(self, widget, path, text):
        self.lstore[path][0] = text

    def _text_edited(self, widget, path, text):
        self.lstore[path][1] = text
