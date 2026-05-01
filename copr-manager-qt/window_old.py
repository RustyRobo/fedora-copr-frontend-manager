import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GObject, Gdk, GLib, Pango
import threading
from backend import copr, dnf_manager, system

class TerminalOutputDialog(Adw.Window):
    def __init__(self, title="Terminal Output", parent=None):
        super().__init__(transient_for=parent, modal=True)
        self.set_title(title)
        self.set_default_size(700, 500)
        
        # Toolbar View
        self.toolbar_view = Adw.ToolbarView()
        self.set_content(self.toolbar_view)
        
        # Header Bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False) # We control closing
        self.toolbar_view.add_top_bar(header)
        
        # Title
        self.title_label = Adw.WindowTitle(title=title, subtitle="Running...")
        header.set_title_widget(self.title_label)
        
        # Content (Scrolled TextView)
        scrolled = Gtk.ScrolledWindow()
        self.toolbar_view.set_content(scrolled)
        
        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_monospace(True)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_bottom_margin(10)
        self.textview.set_top_margin(10)
        self.textview.set_left_margin(10)
        self.textview.set_right_margin(10)
        
        # Style context for black background/terminal look?
        # self.textview.add_css_class("terminal") # if valid
        
        scrolled.set_child(self.textview)
        self.buffer = self.textview.get_buffer()
        
        # Close Button (Initially insensitive)
        self.btn_close = Gtk.Button(label="Close")
        self.btn_close.set_sensitive(False)
        self.btn_close.connect("clicked", self.on_close_clicked)
        header.pack_end(self.btn_close)
        
    def append_line(self, text):
        end_iter = self.buffer.get_end_iter()
        self.buffer.insert(end_iter, text + "\n")
        # Scroll to bottom logic?
        # The TextView usually scrolls if cursor moves? No.
        # We need to manually scroll.
        adj = self.textview.get_vadjustment()
        # Idle add to scroll after resize
        GLib.idle_add(self._scroll_to_bottom, adj)
        
    def _scroll_to_bottom(self, adj):
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return False
        
    def set_finished(self, success):
        self.btn_close.set_sensitive(True)
        self.btn_close.add_css_class("suggested-action")
        if success:
            self.title_label.set_subtitle("Completed Successfully")
            self.append_line("\n--- Operation Completed Successfully ---")
        else:
            self.title_label.set_subtitle("Failed")
            self.append_line("\n--- Operation Failed ---")

    def on_close_clicked(self, btn):
        self.close()

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_default_size(800, 600)
        self.set_title("COPR Manager")

        # System Checks
        if not system.is_fedora():
            self.show_warning("System Warning", "This application is designed for Fedora Linux.")
        elif system.get_fedora_version() != 43:
             # Just a warning as requested
             pass 
             # Wait, user asked for: "Detects Fedora 43 compatibility and warns the user"
             # If it detects it IS Fedora 43, it's fine. 
             # If it detects it is NOT Fedora 43, it should warn.
             # Wait, "Detects Fedora 43 compatibility and warns the user" -> usually means "Warn if NOT compatible" or "Warn if TARGETING 43 but running on X".
             # I'll assume: Warn if NOT Fedora 43.
             self.show_warning("Compatibility Warning", f"You are running Fedora {system.get_fedora_version()}.\nThis tool is optimized for Fedora 43.")

        if not system.has_copr_cli():
            self.show_error("Dependency Missing", "copr-cli is not installed.\nPlease install it via: sudo dnf install copr-cli")

        # Main content structure
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # We need to wrap main_box or replace it with something compatible with AdwViewSwitcher.
        # But AdwApplicationWindow content is usually the whole window content.
        # Let's use Adw.ToolbarView which is modern, but let's stick to HeaderBar + Box + ViewStack for simplicity.
        
        self.set_content(self.main_box)

        # Header Bar
        self.header = Adw.HeaderBar()
        self.main_box.append(self.header)
        
        # View Switcher Title in Header
        self.view_switcher_title = Adw.ViewSwitcherTitle()
        self.view_switcher_title.set_title("COPR Manager")
        self.header.set_title_widget(self.view_switcher_title)

        # View Stack
        self.view_stack = Adw.ViewStack()
        self.view_switcher_title.set_stack(self.view_stack)
        
        # We need to make the stack expand
        self.view_stack.set_vexpand(True)
        self.main_box.append(self.view_stack)
        
        # --- Page 1: Search ---
        self.search_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.view_stack.add_named(self.search_page_box, "search")
        
        # Set page details for switcher
        page_search = self.view_stack.get_page(self.search_page_box)
        page_search.set_title("Search")
        page_search.set_icon_name("system-search-symbolic")

        # Search Bar
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search COPR repositories...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        
        self.clamp = Adw.Clamp(maximum_size=500)
        self.clamp.set_child(self.search_entry)
        self.clamp.set_margin_top(20)
        self.clamp.set_margin_bottom(20)
        
        self.search_page_box.append(self.clamp)
        
        # Spinner for search activity (below search bar)
        self.header_spinner = Gtk.Spinner()
        self.header_spinner.set_size_request(32, 32)
        self.header_spinner.set_halign(Gtk.Align.CENTER)
        self.header_spinner.set_margin_bottom(10)
        self.header_spinner.set_vexpand(True) # Make it take space to look "bigger" in layout? No, strict size is better.
        self.search_page_box.append(self.header_spinner)

        # Results List (Search)
        self.results_listbox = Gtk.ListBox()
        self.results_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.results_listbox.add_css_class("boxed-list")
        self.results_listbox.connect("row-activated", self.on_repo_row_activated)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_child(self.results_listbox)
        self.scrolled.set_vexpand(True)
        
        self.results_clamp = Adw.Clamp(maximum_size=800)
        self.results_clamp.set_child(self.scrolled)
        self.results_clamp.set_margin_bottom(20)
        self.results_clamp.set_margin_start(20)
        self.results_clamp.set_margin_end(20)

        self.search_page_box.append(self.results_clamp)
        
        # Welcome Status Page
        self.welcome_status = Adw.StatusPage()
        self.welcome_status.set_title("Welcome to COPR Manager")
        self.welcome_status.set_description("Search and enable community repositories for Fedora.")
        self.welcome_status.set_icon_name("system-search-symbolic")
        self.welcome_status.set_vexpand(True)
        
        # We want to show this instead of results when empty.
        # But we also have the search entry at top.
        # Let's wrap results and status in a Stack or just toggle visibility.
        self.search_page_box.append(self.welcome_status)
        
        # Initially hide results
        self.results_clamp.set_visible(False)
        self.status_label = Gtk.Label(label="") # Keep reference if needed or remove usage
        # self.search_page_box.append(self.status_label) # Removed as requested
        
        # --- Page 2: Installed ---
        self.installed_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.view_stack.add_named(self.installed_page_box, "installed")
        
        page_installed = self.view_stack.get_page(self.installed_page_box)
        page_installed.set_title("Installed")
        page_installed.set_icon_name("software-installed-symbolic")
        
        self.installed_scrolled = Gtk.ScrolledWindow()
        self.installed_scrolled.set_vexpand(True)
        self.installed_page_box.append(self.installed_scrolled)
        
        self.installed_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.installed_content.set_margin_top(20)
        self.installed_content.set_margin_bottom(20)
        self.installed_content.set_margin_start(20)
        self.installed_content.set_margin_end(20)
        
        self.installed_clamp = Adw.Clamp(maximum_size=800)
        self.installed_clamp.set_child(self.installed_content)
        self.installed_scrolled.set_child(self.installed_clamp)
        
        # Enabled Section
        self.grp_enabled = Adw.PreferencesGroup(title="Enabled Repositories")
        self.installed_content.append(self.grp_enabled)
        # We can use a ListBox inside, or Adw.PreferencesGroup logic.
        # Adw.PreferencesGroup handles rows nicely. But we used ListBox before.
        # Let's stick to Adw.PreferencesGroup as container for ActionRows?
        # Yes, add(row).
        
        # Disabled Section
        self.grp_disabled = Adw.PreferencesGroup(title="Disabled Repositories")
        self.installed_content.append(self.grp_disabled)
        
        # Load installed repos
        self.enabled_repos_set = set() # still need this for checking status elsewhere
        self.load_installed_repos()
        
        self.load_css()
    
    def load_css(self):
        css_provider = Gtk.CssProvider()
        css = b"""
        .badge {
            padding: 2px 8px;
            border-radius: 12px;
            background-color: alpha(currentColor, 0.1);
            font-weight: bold;
            font-size: 0.85em;
        }
        """
        css_provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), 
            css_provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def is_repo_enabled(self, full_name):
        return full_name in self.enabled_repos_set

    def load_installed_repos(self):
        # We need to fetch both configured list and enabled status
        thread = threading.Thread(target=self.fetch_installed_repos)
        thread.daemon = True
        thread.start()
        
    def fetch_installed_repos(self):
        mgr = dnf_manager.DNFManager()
        all_repos = mgr.list_configured_coprs()
        
        # list_configured_coprs now returns 'enabled' status based on 'dnf copr list' output.
        # This is more reliable and faster than running dnf repolist enabled separately.
        
        from gi.repository import GLib
        GLib.idle_add(self.update_installed_list, all_repos)

    def update_installed_list(self, repos):
        # Update global set for DetailsWindow usage
        self.enabled_repos_set.clear()
        
        # Helper to clear a preference group
        def clear_group(grp):
            while True:
                # AdwPreferencesGroup is a widget, iterate its children?
                # No, standard Gtk way to remove children isn't always direct for composites.
                # However, we added rows via .add().
                # Let's try to remove rows.
                # Since we don't have direct access to internal list, we might need to recreate the groups
                # OR use a known method.
                # Actually, simply removing the group and recreating it is safer and cleaner as done below.
                break
            
        # Recreate Groups to clear them
        # Note: referencing them by name to remove from parent
        self.installed_content.remove(self.grp_enabled)
        self.installed_content.remove(self.grp_disabled)
        
        self.grp_enabled = Adw.PreferencesGroup(title="Enabled Repositories")
        self.installed_content.append(self.grp_enabled)
        
        self.grp_disabled = Adw.PreferencesGroup(title="Disabled Repositories")
        self.installed_content.append(self.grp_disabled)

        if repos:
            for r in repos:
                self.add_installed_repo_row(r)
                if r.get('enabled'):
                    self.enabled_repos_set.add(r.get('full_name'))
        else:
             # Add a placeholder if empty?
             pass

    def add_installed_repo_row(self, repo):
        # Similar to ActionRow but for Installed page
        row = Adw.ActionRow()
        row.set_title(repo.get('full_name', 'Unknown'))
        
        # Determine group
        is_enabled = repo.get('enabled', False)
        
        row.set_subtitle(repo.get('description', ''))
        
        # Action Box
        box = Gtk.Box(spacing=10)
        box.set_valign(Gtk.Align.CENTER)
        
        # Action Button (Enable or Disable)
        if is_enabled:
            btn_action = Gtk.Button(icon_name="media-playback-pause-symbolic") # Disable icon? Or user-trash?
            # User requested "Enable" and "Remove" (Delete). 
            # And "Disable".
            # Implementation plan: 
            # Enabled: Disable btn
            # Disabled: Enable btn
            # All: Delete btn
            
            btn_action.set_tooltip_text("Disable")
            btn_action.add_css_class("flat")
            btn_action.connect("clicked", self.on_disable_clicked, repo)
        else:
            btn_action = Gtk.Button(icon_name="media-playback-start-symbolic") # Enable
            btn_action.set_tooltip_text("Enable")
            btn_action.add_css_class("flat")
            btn_action.add_css_class("suggested-action")
            btn_action.connect("clicked", self.on_enable_clicked_from_list, repo)
            
        box.append(btn_action)
        
        # Remove (Delete Config) Button - Always visible
        btn_remove = Gtk.Button(icon_name="user-trash-symbolic")
        btn_remove.add_css_class("flat")
        btn_remove.add_css_class("destructive-action")
        btn_remove.set_tooltip_text("Remove configuration")
        btn_remove.connect("clicked", self.on_remove_repo_clicked, repo)
        box.append(btn_remove)
        
        # Packages Button (Only if enabled?)
        # User said "Open Packages"
        # If disabled, dnf might not list packages easily. 
        # So enable only if enabled.
        btn_pkgs = Gtk.Button(label="Packages")
        btn_pkgs.set_sensitive(is_enabled)
        if is_enabled:
            btn_pkgs.connect("clicked", self.on_packages_clicked, repo)
        box.append(btn_pkgs)
        
        row.add_suffix(box)
        
        if is_enabled:
            self.grp_enabled.add(row)
        else:
            self.grp_disabled.add(row)


    def on_search_changed(self, entry):
        query = entry.get_text()
        if len(query) == 0:
            self.welcome_status.set_visible(True)
            self.results_clamp.set_visible(False)
            return

        if len(query) < 3:
            return
        
        # self.status_label.set_text("Searching...") # Removed label
        
        # Run search in background
        self.header_spinner.start()
        self.header_spinner.set_visible(True)
        
        thread = threading.Thread(target=self.perform_search, args=(query,))
        thread.daemon = True
        thread.start()

    def perform_search(self, query):
        results = copr.search_copr(query)
        # Update UI in main thread
        from gi.repository import GLib
        GLib.idle_add(self.update_results, results)

    def update_results(self, results):
        self.header_spinner.stop()
        self.header_spinner.set_visible(False)
        
        # Clear existing
        while True:
            row = self.results_listbox.get_first_child()
            if not row:
                break
            self.results_listbox.remove(row)
        
        if not results:
            # Show "No results" status? Or just empty list?
            # Let's re-use welcome status but change text? 
            # Or dedicated no results status.
            # For now, let's just show the list (empty) and maybe a toast?
            # Or better, use StatusPage for "No Results".
            self.welcome_status.set_title("No Results Found")
            self.welcome_status.set_description("Try a different search query.")
            self.welcome_status.set_icon_name("edit-find-symbolic")
            self.welcome_status.set_visible(True)
            self.results_clamp.set_visible(False)
            return

        # Show results
        self.welcome_status.set_visible(False)
        self.results_clamp.set_visible(True)
        # Reset welcome text for next time (optional, or reset on clear)
        self.welcome_status.set_title("Welcome to COPR Manager") 
        self.welcome_status.set_description("Search and enable community repositories for Fedora.")
        self.welcome_status.set_icon_name("system-search-symbolic")

        # self.status_label.set_text(f"Found {len(results)} repositories.") # Removed label

        for repo in results:
            self.add_repo_row(repo)

    def show_warning(self, title, message):
        self.show_dialog(title, message, "dialog-warning")

    def show_error(self, title, message):
        self.show_dialog(title, message, "dialog-error")

    def show_dialog(self, title, message, icon_name):
        # Using Adw.MessageDialog if available or Gtk.MessageDialog
        # Since we are an Adw.ApplicationWindow, let's use Adw.MessageDialog
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=title,
            body=message
        )
        dialog.add_response("ok", "OK")
        dialog.present()

    def get_badges(self, repo):
        badges = []
        full_name = repo.get('full_name', '').lower()
        desc = repo.get('description', '').lower()
        owner = repo.get('owner', '').lower()
        
        # 1. Official / Quasi-Official
        if owner in ['fedora', 'copr', '@copr', '@fedora']:
            badges.append(('Official', 'accent'))
        elif owner.startswith('@'):
            badges.append(('Group', 'neutral'))
            
        # 2. Languages / Tech
        keywords = {
            'python': 'Python',
            'rust': 'Rust', 
            'golang': 'Go',
            'go ': 'Go',
            'c++': 'C++',
            'ruby': 'Ruby',
            'java': 'Java',
            'nodejs': 'Node',
            'flask': 'Python',
            'django': 'Python',
            'gtk': 'GTK',
            'qt': 'Qt'
        }
        
        found_tech = set()
        for k, v in keywords.items():
            if k in desc or k in full_name:
                found_tech.add(v)
        
        # Limit to 2 tech badges to avoid clutter
        for tech in list(found_tech)[:2]:
            badges.append((tech, 'success'))
            
        # 3. Desktop / Environment
        desktops = {
            'gnome': 'GNOME',
            'kde': 'KDE',
            'cosmic': 'Cosmic',
            'hyprland': 'Hyprland',
            'sway': 'Sway',
            'xfce': 'XFCE'
        }
        for k, v in desktops.items():
            if k in desc or k in full_name:
                badges.append((v, 'warning'))
                
        return badges

    def get_github_url(self, repo):
        # Check homepage
        homepage = repo.get('homepage')
        if homepage and 'github.com' in homepage:
            return homepage
        
        # Check instructions (maybe safe to specific regex)
        # For now, just homepage is safer to avoid random links.
        return None

    def add_repo_row(self, repo):
        # repo is a dict: {'full_name': 'owner/project', 'description': '...'}
        row = Adw.ActionRow()
        row.set_title(repo.get('full_name', 'Unknown Repos'))
        
        raw_subtitle = repo.get('description', '') or ""
        # Helper to limit text length
        clean_desc = raw_subtitle[:100].replace('\n', ' ')
        
        # Escape markup characters
        from gi.repository import GLib
        escaped_desc = GLib.markup_escape_text(clean_desc)
        
        row.set_subtitle(escaped_desc) 
        
        # Make row clickable
        row.set_activatable(True)
        # Bind data
        row._repo_data = repo
        
        # --- Badges Suffix ---
        # We use a box to hold badges
        badges_box = Gtk.Box(spacing=6)
        badges_box.set_valign(Gtk.Align.CENTER)
        
        badges = self.get_badges(repo)
        for text, style in badges:
            lbl = Gtk.Label(label=text)
            lbl.add_css_class("badge") # Check if Adwaita has .badge, usually custom css needed or .pill
            # .activatable .suggested-action etc are for buttons.
            # Using Gtk generic classes: .dim-label etc.
            # Adwaita doesn't have pill badges by default for Labels without custom CSS.
            # We can use a button that looks like a badge or custom CSS.
            # Let's use simple labels with styling context.
            # Or use a Frame/Background.
            # Workaround: Use a Button with .flat and specific class, non-clickable?
            # Better: Adw.Bin? 
            # Let's use custom CSS in main? Or just text for now?
            # User wants "Pill-shaped badges". 
            # I will wrap label in a box and add css class if possible, or use .numeric class?
            # Let's try adding a style class to the label and hope for the best, or style it later.
            # Actually, let's use a tiny frame or just styled label.
            # standard style: .accent, .success, .warning, .error exist for text color.
            lbl.add_css_class(style) 
            lbl.add_css_class("body")
            lbl.add_css_class("caption") # smaller text
            # To make it look like a badge, we need background. 
            # Without custom CSS, we can't easily do pills. 
            # I will rely on text color for now, or use `Gtk.LevelBar`? No.
            # Let's just use colored text.
            badges_box.append(lbl)
            
        row.add_suffix(badges_box)
        
        # Arrow suffix
        row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        
        self.results_listbox.append(row)

    def on_repo_row_activated(self, listbox, row):
        if not hasattr(row, '_repo_data'):
            return
        
        repo = row._repo_data
        # Open Details Window
        details = RepoDetailsWindow(repo, self)
        details.present()

    def on_enable_clicked(self, btn, repo):
        self._generic_repo_action(repo, "enable")
        
    def on_enable_clicked_from_list(self, btn, repo):
        self._generic_repo_action(repo, "enable")

    def on_disable_clicked(self, btn, repo):
        self._generic_repo_action(repo, "disable")
        
    def _generic_repo_action(self, repo, action):
        full_name = repo.get('full_name')
        if not full_name:
            return
            
        owner, project = full_name.split('/', 1)
        
        # Create and show terminal dialog
        title_map = {
            "enable": f"Enabling {full_name}",
            "disable": f"Disabling {full_name}",
            "remove": f"Removing {full_name}"
        }
        
        dlg = TerminalOutputDialog(title=title_map.get(action, "Processing"), parent=self)
        dlg.present()
        
        def run_action():
            mgr = dnf_manager.DNFManager()
            
            # Callback to update dialog from thread
            def output_cb(line):
                from gi.repository import GLib
                GLib.idle_add(dlg.append_line, line)
            
            success = False
            if action == "enable":
                success = mgr.enable_repo(owner, project, output_cb=output_cb)
            elif action == "disable":
                success = mgr.disable_repo(owner, project, output_cb=output_cb)
            elif action == "remove":
                success = mgr.remove_repo(owner, project, output_cb=output_cb)
                
            from gi.repository import GLib
            GLib.idle_add(self.on_repo_action_finished, success, full_name, action, dlg)
            
        thread = threading.Thread(target=run_action)
        thread.daemon = True
        thread.start()

    def on_repo_action_finished(self, success, full_name, action, dlg):
        dlg.set_finished(success)
        
        # When dialog is closed (or immediately?), we refresh list.
        # But we probably want to refresh background list immediately so main UI updates when dialog closes.
        # But user sees the dialog.
        
        if success:
             self.load_installed_repos()
             
        # We don't need show_dialog success/error because TerminalOutputDialog shows it.
        # But we might want to update some other UI state.
        
    def on_remove_repo_clicked(self, btn, repo):
        full_name = repo.get('full_name')
        
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Remove Repository?",
            body=f"Are you sure you want to remove the configuration for {full_name}?\nThis will delete the .repo file.",
        )
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        
        def response_cb(dlg, response):
            if response == "remove":
                self._generic_repo_action(repo, "remove")
        
        dialog.connect("response", response_cb)
        dialog.present()

    # Legacy methods removed/replaced or redirected
    # We remove on_enable_finished, on_disable_finished, on_remove_repo_finished usage
    # but keep on_enable_finished logic inside on_repo_action_finished effectively.
    
    # We need to make sure we didn't break anything calling on_enable_finished elsewhere? 
    # No, they were only called from these actions.
    
    # However, we must ensure the older methods are gone or unused to avoid confusion.
    # I am replacing lines 506 to 643 which covers most of them.



    def on_packages_clicked(self, btn, repo):
        full_name = repo.get('full_name')
        if not full_name:
            return
        
        win = PackagesWindow(repo=repo, transient_for=self)
        win.present()

class RepoDetailsWindow(Adw.Window):
    def __init__(self, repo, parent_window):
        super().__init__(transient_for=parent_window, modal=True)
        self.repo = repo
        self.parent_window = parent_window
        self.set_title("Repository Details")
        self.set_default_size(600, 500)
        
        # Main Layout
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.box)
        
        # Header
        self.header = Adw.HeaderBar()
        self.box.append(self.header)
        
        # Content Scroll
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.box.append(self.scrolled)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.content_box.set_margin_top(20)
        self.content_box.set_margin_bottom(20)
        self.content_box.set_margin_start(20)
        self.content_box.set_margin_end(20)
        self.scrolled.set_child(self.content_box)
        
        # Title
        lbl_title = Gtk.Label(label=repo.get('full_name', 'Unknown'))
        lbl_title.add_css_class("title-1")
        lbl_title.set_justify(Gtk.Justification.CENTER)
        self.content_box.append(lbl_title)
        
        # Description
        desc_frame = Adw.PreferencesGroup(title="Description")
        self.content_box.append(desc_frame)
        
        desc = repo.get('description', 'No description available.')
        lbl_desc = Gtk.Label(label=desc)
        lbl_desc.set_wrap(True)
        lbl_desc.set_xalign(0)
        # Wrap safely in a box or row? PrefGroup handles rows.
        # Let's simpler: just Label.
        # Actually Adw.PreferencesGroup expects rows.
        # Let's use Adw.ActionRow with label? Or just append content directly?
        # Adw.PreferencesGroup has add(child).
        desc_frame.add(lbl_desc)

        # Instructions
        instr_frame = Adw.PreferencesGroup(title="Instructions")
        self.content_box.append(instr_frame)
        
        instr = repo.get('instructions', 'No specific instructions provided.')
        lbl_instr = Gtk.Label(label=instr)
        lbl_instr.set_wrap(True)
        lbl_instr.set_xalign(0)
        lbl_instr.set_selectable(True)
        instr_frame.add(lbl_instr)
        
        # Metadata Info (Owner, Homepage, Contact, Versions)
        meta_frame = Adw.PreferencesGroup(title="Metadata")
        self.content_box.append(meta_frame)
        
        # Supported Versions
        # Parse chroots if available
        # Expecting dict: {'fedora-43-x86_64': ..., 'fedora-42-x86_64': ...}
        # or list of keys?
        chroots = repo.get('chroots')
        if chroots:
            versions = set()
            # If standard copr object, chroots is a dict (chroot name -> url)
            # Keys look like: fedora-43-x86_64, fedora-rawhide-x86_64, epel-9-x86_64
            
            # If it's a list, iterate. If dict, iterate keys.
            iterable = chroots.keys() if isinstance(chroots, dict) else chroots
            
            for chroot in iterable:
                parts = chroot.split('-')
                # heuristics:
                if 'fedora' in parts:
                    try:
                        idx = parts.index('fedora')
                        ver = parts[idx+1]
                        if ver.isdigit() or ver == 'rawhide':
                            versions.add(f"Fedora {ver}")
                    except (IndexError, ValueError):
                        pass
                elif 'epel' in parts:
                    try:
                         idx = parts.index('epel')
                         ver = parts[idx+1]
                         versions.add(f"EPEL {ver}")
                    except:
                        pass
            
            if versions:
                sorted_vers = sorted(list(versions), key=lambda x: x.split()[-1], reverse=True)
                row_ver = Adw.ActionRow()
                row_ver.set_title("Supported Versions")
                row_ver.set_subtitle(", ".join(sorted_vers))
                meta_frame.add(row_ver)

        # Size / Package Count
        # If we had 'storage_usage' or 'package_count' from API we could show it.
        # Currently standard search result might not have it.
        # We can try to show "N/A" or fetch it.
        # Let's add a placeholder row for now, or check generic 'size' attr.
        size_bytes = repo.get('storage_usage')
        if size_bytes:
             # Convert to MB/GB
             try:
                 size_mb = int(size_bytes) / 1024 / 1024
                 row_size = Adw.ActionRow()
                 row_size.set_title("Storage Usage")
                 row_size.set_subtitle(f"{size_mb:.1f} MB")
                 meta_frame.add(row_size)
             except:
                 pass
        
        # Homepage
        
        # Homepage
        homepage = repo.get('homepage')
        if homepage:
            row_home = Adw.ActionRow()
            row_home.set_title("Homepage")
            row_home.set_subtitle(homepage)
            # Make it a link button?
            # Or copy button?
            # For now simplified.
            meta_frame.add(row_home)
            
        # Contact
        contact = repo.get('contact')
        if contact:
            row_contact = Adw.ActionRow()
            row_contact.set_title("Contact")
            row_contact.set_subtitle(str(contact))
            meta_frame.add(row_contact)
            
        # Actions
        self.bottom_bar = Gtk.Box(spacing=10)
        self.bottom_bar.set_margin_top(10)
        self.bottom_bar.set_margin_bottom(20)
        self.bottom_bar.set_halign(Gtk.Align.CENTER)
        self.content_box.append(self.bottom_bar)
        
        full_name = repo.get('full_name')
        is_enabled = self.parent_window.is_repo_enabled(full_name)
        
        if is_enabled:
            # Show "Open Packages" and "Remove/Disable"
            self.btn_pkgs = Gtk.Button(label="Open Packages")
            self.btn_pkgs.connect("clicked", self.on_open_packages)
            self.bottom_bar.append(self.btn_pkgs)
            
            self.btn_disable = Gtk.Button(label="Disable Repository")
            self.btn_disable.add_css_class("destructive-action")
            self.btn_disable.connect("clicked", self.on_disable_clicked)
            self.bottom_bar.append(self.btn_disable)
            
        else:
            self.btn_enable = Gtk.Button(label="Enable Repository")
            self.btn_enable.add_css_class("suggested-action")
            self.btn_enable.add_css_class("pill")
            self.btn_enable.connect("clicked", self.on_enable_clicked)
            self.bottom_bar.append(self.btn_enable)

    def on_open_packages(self, btn):
        self.parent_window.on_packages_clicked(btn, self.repo)
        self.close()

    def on_disable_clicked(self, btn):
        # We need a disable logic in main or here.
        # Main has on_enable_clicked but not on_disable_clicked.
        # Let's add it to main or handle it here?
        # Better in main to keep DNF logic there.
        # But wait, main only has enable.
        # Let's call parent method `on_disable_clicked` (to be created)
        if hasattr(self.parent_window, 'on_disable_clicked'):
             self.parent_window.on_disable_clicked(btn, self.repo)
        else:
             print("Error: on_disable_clicked not implemented in MainWindow")
        self.close()

    def on_enable_clicked(self, btn):
        
        # Source Button (if detected)
        # Helper to get GitHub url
        github_url = self.parent_window.get_github_url(repo)
        if github_url:
            self.btn_source = Gtk.Button(icon_name="text-x-script-symbolic", label="Source") # or specific icon
            # Use 'web-browser-symbolic' or similar
            self.btn_source.set_icon_name("web-browser-symbolic") 
            self.btn_source.set_label("Source Code")
            self.btn_source.add_css_class("flat")
            
            def open_url(*args):
                launcher = Gtk.UriLauncher(uri=github_url)
                launcher.launch(self, None, None)
                
            self.btn_source.connect("clicked", open_url)
            self.bottom_bar.append(self.btn_source)

    def on_enable_clicked(self, btn):
        # Call parent's enable logic?
        # We can duplicate logic or call parent method.
        # Parent method requires button and repo args.
        # Let's call parent.on_enable_clicked(btn, self.repo).
        # But parent expects btn to replace text etc.
        # Let's reuse logic.
        self.parent_window.on_enable_clicked(btn, self.repo)
        self.close()



class PackagesWindow(Adw.Window):
    def __init__(self, repo, **kwargs):
        super().__init__(**kwargs)
        self.repo = repo
        self.set_title(f"Packages: {repo.get('full_name')}")
        self.set_default_size(600, 500)
        
        # Main Layout
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.box)
        
        # Header
        self.header = Adw.HeaderBar()
        self.box.append(self.header)
        
        # List
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_vexpand(True)
        self.scrolled.set_child(self.listbox)
        self.box.append(self.scrolled)
        
        # Status
        self.status = Gtk.Label(label="Loading packages...")
        self.status.set_margin_bottom(10)
        self.status.set_margin_top(10)
        self.box.append(self.status)
        
        self.load_packages()

    def load_packages(self):
        full_name = self.repo.get('full_name')
        # We need a proper repo ID. Assuming standard format copr:copr.fedorainfracloud.org:owner:project
        # But dnf might be picky.
        # Let's try to guess or search available repos.
        # For simplicity, we assume `dnf repository-packages` works with `copr:copr.fedorainfracloud.org:owner:project`
        # Or more reliably, we might need to list repos first.
        # Let's try constructing the ID:
        owner, project = full_name.split('/', 1)
        repo_id = f"copr:copr.fedorainfracloud.org:{owner}:{project}"
        
        thread = threading.Thread(target=self.fetch_packages, args=(repo_id,))
        thread.daemon = True
        thread.start()

    def update_list(self, pkgs, repo_id):
        if not pkgs:
            self.status.set_text(f"No packages found or repo not enabled/found ({repo_id}).")
            return
            
        self.status.set_text(f"Found {len(pkgs)} packages.")
        
        # Helper to check installation in background or bulk? 
        # Checking one by one in main thread might be slow if many packages.
        # But usually a repo has few packages. Let's do it in the loop for now, 
        # but optimally we should fetch status in the background thread.
        # Since we are already in the main thread here (idle_add), 
        # checking rpm -q for 50 packages might freeze UI. 
        # Let's fire a thread to check status for each row? Or just check all in background before calling update_list?
        # Better: check all in background before calling update_list.
        # So wait, let's refactor fetch_packages.
        pass

    def fetch_packages(self, repo_id):
        mgr = dnf_manager.DNFManager()
        pkgs = mgr.list_packages(repo_id)
        
        # Check status
        pkg_status = {}
        for p in pkgs:
            pkg_status[p] = mgr.is_package_installed(p)
            
        from gi.repository import GLib
        GLib.idle_add(self.update_list_with_status, pkgs, pkg_status, repo_id)

    def update_list_with_status(self, pkgs, pkg_status, repo_id):
        if not pkgs:
            self.status.set_text(f"No packages found or repo not enabled/found ({repo_id}).")
            return

        self.status.set_text(f"Found {len(pkgs)} packages.")
        
        # Clear list just in case
        while True:
            row = self.listbox.get_first_child()
            if not row:
                break
            self.listbox.remove(row)

        for pkg in pkgs:
            row = Adw.ActionRow()
            row.set_title(pkg)
            
            is_installed = pkg_status.get(pkg, False)
            
            if is_installed:
                btn = Gtk.Button(label="Remove") # or Uninstall
                btn.add_css_class("destructive-action")
                btn.connect("clicked", self.on_remove_clicked, pkg)
            else:
                btn = Gtk.Button(label="Install")
                btn.add_css_class("suggested-action")
                btn.connect("clicked", self.on_install_clicked, pkg)
            
            btn.set_valign(Gtk.Align.CENTER)
            row.add_suffix(btn)
            self.listbox.append(row)

    def do_install_from_preview(self, pkg_name):
        self._generic_package_action(pkg_name, "install")

    def perform_install_no_btn(self, pkg):
        # Redirect
        self._generic_package_action(pkg, "install")

    def on_install_clicked(self, btn, pkg):
        # Show preview dialog
        preview_dialog = PreviewDialog(pkg, self)
        preview_dialog.present()

    def perform_install(self, btn, pkg):
        self._generic_package_action(pkg, "install")

    def on_remove_clicked(self, btn, pkg):
        # Confirm?
        # dnf remove -y is destructive.
        # Let's show terminal dialog directly for now as user asked for streaming output.
        self._generic_package_action(pkg, "remove")

    def perform_remove(self, btn, pkg):
        self._generic_package_action(pkg, "remove")

    def _generic_package_action(self, pkg_name, action):
        # Create and show terminal dialog
        title_map = {
            "install": f"Installing {pkg_name}",
            "remove": f"Removing {pkg_name}"
        }
        
        dlg = TerminalOutputDialog(title=title_map.get(action, "Processing"), parent=self)
        dlg.present()
        
        def run_action():
            mgr = dnf_manager.DNFManager()
            
            # Callback
            def output_cb(line):
                from gi.repository import GLib
                GLib.idle_add(dlg.append_line, line)
            
            success = False
            if action == "install":
                success = mgr.install_package(pkg_name, output_cb=output_cb)
            elif action == "remove":
                success = mgr.remove_package(pkg_name, output_cb=output_cb)
                
            from gi.repository import GLib
            GLib.idle_add(self.on_action_finished, success, dlg)
            
        thread = threading.Thread(target=run_action)
        thread.daemon = True
        thread.start()

    def on_action_finished(self, success, dlg):
        dlg.set_finished(success)
        
        if success:
            # We need to reload the package list and status
            self.status.set_text("Action successful. Refreshing...")
            self.load_packages()
        else:
            self.status.set_text("Action failed. Check logs.")
            self.load_packages()

class PreviewDialog(Adw.Window):
    def __init__(self, pkg_name, parent_window):
        super().__init__(transient_for=parent_window, modal=True)
        self.set_title(f"Install Preview: {pkg_name}")
        self.set_default_size(500, 400)
        
        self.pkg_name = pkg_name
        self.parent_window = parent_window
        
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.set_margin_top(10)
        self.box.set_margin_bottom(10)
        self.box.set_margin_start(10)
        self.box.set_margin_end(10)
        self.set_content(self.box)
        
        # Header
        lbl = Gtk.Label(label=f"Previewing changes for {pkg_name}...")
        lbl.add_css_class("title-3")
        self.box.append(lbl)
        
        # Spinner
        self.spinner = Gtk.Spinner()
        self.spinner.start()
        self.box.append(self.spinner)
        
        # Content content
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.box.append(self.content_box)
        
        # Actions
        self.actions_box = Gtk.Box(spacing=10, halign=Gtk.Align.CENTER)
        self.box.append(self.actions_box)
        
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda x: self.close())
        self.actions_box.append(btn_cancel)
        
        self.btn_confirm = Gtk.Button(label="Confirm Install")
        self.btn_confirm.add_css_class("suggested-action")
        self.btn_confirm.set_sensitive(False)
        self.btn_confirm.connect("clicked", self.on_confirm)
        self.actions_box.append(self.btn_confirm)
        
        self.start_preview()
        
    def start_preview(self):
        thread = threading.Thread(target=self.fetch_preview)
        thread.daemon = True
        thread.start()
        
    def fetch_preview(self):
        from backend.preview import PreviewManager
        mgr = PreviewManager()
        changes = mgr.get_install_preview(self.pkg_name)
        
        from gi.repository import GLib
        GLib.idle_add(self.show_preview, changes)
        
    def show_preview(self, changes):
        self.spinner.stop()
        self.spinner.set_visible(False)
        
        if not changes:
            lbl = Gtk.Label(label="Could not determine transaction details.\nIt might be unsafe or package not found.")
            self.content_box.append(lbl)
            # Allow install anyway? Maybe with warning.
            self.btn_confirm.set_sensitive(True)
            return
            
        # Display changes
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_min_content_height(200)
        self.content_box.append(scroll)
        
        # Build text
        text = ""
        for action in ['install', 'upgrade', 'downgrade', 'remove']:
            pkgs = changes.get(action, [])
            if pkgs:
                text += f"<b>{action.upper()}:</b>\n"
                for p in pkgs:
                    text += f" • {p}\n"
                text += "\n"
        
        lbl_content = Gtk.Label(label=text, use_markup=True, xalign=0)
        lbl_content.set_wrap(True)
        scroll.set_child(lbl_content)
        
        self.btn_confirm.set_sensitive(True)

    def on_confirm(self, btn):
        btn.set_sensitive(False)
        btn.set_label("Installing...")
        self.close()
        
        # Trigger install on parent
        # We need to find the specific button in parent to update state?
        # Simpler: Call parent's perform_install manually or trigger callback.
        # But parent on_install_clicked created us.
        # Let's call parent.perform_install logic directly?
        # We don't have the button instance from parent here easily unless we pass it.
        # Let's Modify parent to accept install request without button reference?
        # Or pass callback.
        # For quickly, let's call parent.do_install_from_preview(self.pkg_name)
        self.parent_window.do_install_from_preview(self.pkg_name)





