import Foundation

#if os(macOS)
import AppKit
import Combine

@MainActor
final class LocalMediaLibrary: ObservableObject {
    static let shared = LocalMediaLibrary()

    @Published private(set) var rootURL: URL?

    private let bookmarkKey = "mm.localMediaRootBookmark"
    private var securityScopedURL: URL?

    private init() {
        restoreBookmark()
    }

    var displayPath: String {
        rootURL?.path(percentEncoded: false) ?? ""
    }

    func chooseFolder() {
        let panel = NSOpenPanel()
        panel.title = "Choose Local Media Folder"
        panel.prompt = "Use Folder"
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.canCreateDirectories = false

        if panel.runModal() == .OK, let url = panel.url {
            setRootURL(url)
        }
    }

    func clear() {
        securityScopedURL?.stopAccessingSecurityScopedResource()
        securityScopedURL = nil
        rootURL = nil
        UserDefaults.standard.removeObject(forKey: bookmarkKey)
    }

    func localURL(for mediaPath: String) -> URL? {
        let expanded = (mediaPath as NSString).expandingTildeInPath
        let direct = URL(fileURLWithPath: expanded)
        if direct.path(percentEncoded: false).hasPrefix("/") && FileManager.default.fileExists(atPath: direct.path(percentEncoded: false)) {
            return direct
        }

        guard let rootURL else { return nil }
        let relative = mediaPath
            .trimmingCharacters(in: CharacterSet(charactersIn: "/"))
            .replacingOccurrences(of: "\\", with: "/")
        let url = rootURL.appendingPathComponent(relative)
        return FileManager.default.fileExists(atPath: url.path(percentEncoded: false)) ? url : nil
    }

    private func setRootURL(_ url: URL) {
        do {
            let bookmark = try url.bookmarkData(
                options: [.withSecurityScope],
                includingResourceValuesForKeys: nil,
                relativeTo: nil,
            )
            UserDefaults.standard.set(bookmark, forKey: bookmarkKey)
            securityScopedURL?.stopAccessingSecurityScopedResource()
            securityScopedURL = url
            _ = url.startAccessingSecurityScopedResource()
            rootURL = url
        } catch {
            NSSound.beep()
        }
    }

    private func restoreBookmark() {
        guard let data = UserDefaults.standard.data(forKey: bookmarkKey) else { return }
        do {
            var stale = false
            let url = try URL(
                resolvingBookmarkData: data,
                options: [.withSecurityScope],
                relativeTo: nil,
                bookmarkDataIsStale: &stale,
            )
            guard !stale else {
                clear()
                return
            }
            securityScopedURL = url
            _ = url.startAccessingSecurityScopedResource()
            rootURL = url
        } catch {
            clear()
        }
    }
}
#endif
