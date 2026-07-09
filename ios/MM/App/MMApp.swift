import SwiftUI

@main
struct MMApp: App {
    @State private var auth = AuthStore()

    @SceneBuilder
    var body: some Scene {
        mainWindow
        #if os(macOS)
        menuBar
        #endif
    }

    private var mainWindow: some Scene {
        WindowGroup {
            ContentView()
                .environment(auth)
                .tint(.blue) // Apple systemBlue — matches the web theme accent
                .symbolRenderingMode(.hierarchical) // depth & layered glyphs (HIG)
        }
        #if os(macOS)
        .defaultSize(width: 1100, height: 720)
        .commands {
            CommandGroup(replacing: .newItem) { }
        }
        #endif
    }

    #if os(macOS)
    private var menuBar: some Scene {
        MenuBarExtra("MM", systemImage: "photo.stack") {
            StatusBarSettingsView()
                .environment(auth)
                .frame(width: 380, height: 560)
        }
        .menuBarExtraStyle(.window)
    }
    #endif
}
