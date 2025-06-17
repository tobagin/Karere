# frontend/karere/window.py

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gio, GdkPixbuf
import base64
from io import BytesIO

class ChatRow(Gtk.ListBoxRow):
    def __init__(self, jid, last_message):
        super().__init__()
        self.jid = jid
        self.jid_label = Gtk.Label(label=jid, halign=Gtk.Align.START, ellipsize=3)
        self.jid_label.get_style_context().add_class('title-4')
        self.last_message_label = Gtk.Label(label=last_message, halign=Gtk.Align.START, ellipsize=3)
        self.last_message_label.get_style_context().add_class('body')
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_start=12, margin_end=12, margin_top=8, margin_bottom=8)
        box.append(self.jid_label)
        box.append(self.last_message_label)
        self.set_child(box)

    def update_last_message(self, last_message):
        self.last_message_label.set_label(last_message)

@Gtk.Template(resource_path='/io/github/tobagin/Karere/karere.ui')
class KarereWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'KarereWindow'

    main_stack = Gtk.Template.Child()
    chat_list_box = Gtk.Template.Child()
    qr_image = Gtk.Template.Child()
    qr_spinner = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._chat_rows = {}
        self.main_stack.set_visible_child_name('connecting_view')
        self.qr_spinner.start()

    def add_or_update_chat(self, jid, last_message):
        if jid in self._chat_rows:
            self._chat_rows[jid].update_last_message(last_message)
        else:
            new_row = ChatRow(jid, last_message)
            self._chat_rows[jid] = new_row
            self.chat_list_box.prepend(new_row)

    def show_reconnecting_view(self):
        """Switches the stack to the reconnecting view."""
        self.main_stack.set_visible_child_name('reconnecting_view')
        print("Switched to reconnecting view.")

    def show_qr_view(self):
        self.main_stack.set_visible_child_name('qr_view')
        print("Switched to QR view.")

    def show_qr_code(self, qr_data_url):
        if not qr_data_url or not qr_data_url.startswith('data:image/png;base64,'):
            return
        base64_data = qr_data_url.split(',')[1]
        image_data = base64.b64decode(base64_data)
        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(image_data)
        loader.close()
        pixbuf = loader.get_pixbuf()
        self.qr_spinner.stop()
        self.qr_spinner.set_visible(False)
        self.qr_image.set_from_pixbuf(pixbuf)
        self.qr_image.set_visible(True)
        print("QR Code displayed.")

    def show_chat_view(self):
        self.main_stack.set_visible_child_name('chat_view')
        print("Switched to chat view.")

    def show_toast(self, message):
        toast_overlay = self.get_content()
        toast_overlay.add_toast(Adw.Toast.new(message))
        print(f"Toast: {message}")
