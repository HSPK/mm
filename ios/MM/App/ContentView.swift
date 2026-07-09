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
    #if os(macOS)
    @State private var selection: Sidebar.SidebarItem? = .library
    #endif

    var body: some View {
        #if os(macOS)
        NavigationSplitView {
            Sidebar(selection: $selection)
                .navigationSplitViewColumnWidth(min: 220, ideal: 240, max: 280)
        } detail: {
            NavigationStack {
                sidebarDetail
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
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

    #if os(macOS)
    @ViewBuilder
    private var sidebarDetail: some View {
        switch selection ?? .library {
        case .library: MacLibraryView()
        case .albums: AlbumsView()
        case .map: MapView()
        case .stats: StatsView()
        }
    }
    #endif
}

#if os(macOS)
private struct Sidebar: View {
    @Binding var selection: SidebarItem?

    var body: some View {
        List(selection: $selection) {
            Section("Library") {
                sidebarRow(.library)
                sidebarRow(.albums)
            }
            Section("Explore") {
                sidebarRow(.map)
                sidebarRow(.stats)
            }
        }
        .listStyle(.sidebar)
        .navigationTitle("MM")
    }

    private func sidebarRow(_ item: SidebarItem) -> some View {
        Label(item.title, systemImage: item.systemImage)
            .tag(item)
    }

    enum SidebarItem: String, CaseIterable, Identifiable {
        case library, albums, map, stats

        var id: String { rawValue }

        var title: String {
            switch self {
            case .library: return "All Photos"
            case .albums: return "Albums"
            case .map: return "Places"
            case .stats: return "Insights"
            }
        }

        var systemImage: String {
            switch self {
            case .library: return "photo.stack"
            case .albums: return "rectangle.stack"
            case .map: return "map"
            case .stats: return "chart.xyaxis.line"
            }
        }
    }
}
#endif
