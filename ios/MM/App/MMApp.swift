import SwiftUI

@main
struct MMApp: App {
    @State private var auth = AuthStore()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(auth)
                .preferredColorScheme(.dark)
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
}
