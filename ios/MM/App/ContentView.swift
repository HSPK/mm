import SwiftUI

struct ContentView: View {
    @Environment(AuthStore.self) private var auth

    var body: some View {
        if auth.isAuthenticated {
            SignedInRoot()
        } else {
            LoginView()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background(WindowBackground())
        }
    }
}

private struct WindowBackground: View {
    var body: some View {
        #if os(macOS)
        Color(nsColor: .windowBackgroundColor)
        #else
        Color(uiColor: .systemBackground)
        #endif
    }
}

private struct SignedInRoot: View {
    var body: some View {
        #if os(macOS)
        NavigationSplitView {
            Sidebar()
                .navigationSplitViewColumnWidth(min: 200, ideal: 220)
        } detail: {
            NavigationStack {
                LibraryView()
            }
        }
        #else
        TabView {
            NavigationStack {
                LibraryView()
            }
            .tabItem { Label("Library", systemImage: "photo.on.rectangle") }

            NavigationStack {
                AlbumsView()
            }
            .tabItem { Label("Albums", systemImage: "rectangle.stack") }

            NavigationStack {
                MapView()
            }
            .tabItem { Label("Map", systemImage: "map") }

            NavigationStack {
                StatsView()
            }
            .tabItem { Label("Stats", systemImage: "chart.bar") }

            NavigationStack {
                SettingsView()
            }
            .tabItem { Label("Settings", systemImage: "gear") }
        }
        #endif
    }
}

#if os(macOS)
private struct Sidebar: View {
    @State private var selection: SidebarItem? = .library

    var body: some View {
        List(selection: $selection) {
            NavigationLink(value: SidebarItem.library) {
                Label("Library", systemImage: "photo.on.rectangle")
            }
            NavigationLink(value: SidebarItem.albums) {
                Label("Albums", systemImage: "rectangle.stack")
            }
            NavigationLink(value: SidebarItem.map) {
                Label("Map", systemImage: "map")
            }
            NavigationLink(value: SidebarItem.stats) {
                Label("Stats", systemImage: "chart.bar")
            }
            NavigationLink(value: SidebarItem.settings) {
                Label("Settings", systemImage: "gear")
            }
        }
        .navigationTitle("MM")
        .navigationDestination(for: SidebarItem.self) { item in
            switch item {
            case .library: LibraryView()
            case .albums: AlbumsView()
            case .map: MapView()
            case .stats: StatsView()
            case .settings: SettingsView()
            }
        }
    }

    enum SidebarItem: Hashable { case library, albums, map, stats, settings }
}
#endif
