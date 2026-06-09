import SwiftUI

struct SettingsView: View {
    @Environment(AuthStore.self) private var auth
    @State private var apiBaseURL = AppConfig.apiBaseURL.absoluteString
    @State private var savedURL = false

    @State private var currentLibrary: LibraryInfo?
    @State private var recentLibraries: [LibraryInfo] = []
    @State private var loadingLibrary = false
    @State private var libraryError: String?
    @State private var switching = false
    @State private var newLibraryPath = ""

    private let libraryRepo = LibraryRepository.shared

    var body: some View {
        Form {
            if let user = auth.user {
                Section("Signed in") {
                    HStack(spacing: 14) {
                        Text(user.initial)
                            .font(.title2.weight(.bold))
                            .foregroundStyle(.tint)
                            .frame(width: 44, height: 44)
                            .background(.tint.opacity(0.15), in: .circle)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(user.displayName.isEmpty ? user.username : user.displayName)
                                .font(.body.weight(.semibold))
                            Text("@\(user.username)")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        if user.isAdmin {
                            Label("Admin", systemImage: "checkmark.seal.fill")
                                .font(.caption2.weight(.semibold))
                                .foregroundStyle(.green)
                        }
                    }
                    .padding(.vertical, 2)

                    Button(role: .destructive, action: auth.signOut) {
                        Label("Sign out", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }
            }

            Section("Server") {
                TextField("API base URL", text: $apiBaseURL)
                    #if os(iOS)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .keyboardType(.URL)
                    #endif
                Button {
                    if let url = URL(string: apiBaseURL), url.scheme != nil {
                        AppConfig.setAPIBaseURL(url)
                        savedURL = true
                    }
                } label: {
                    Label(savedURL ? "Saved" : "Save", systemImage: savedURL ? "checkmark.circle.fill" : "tray.and.arrow.down")
                }
                .disabled(apiBaseURL.isEmpty)
            }

            librarySection

            Section("About") {
                LabeledContent("Version") {
                    Text(version)
                        .monospacedDigit()
                        .foregroundStyle(.secondary)
                }
                Link(destination: URL(string: "https://github.com/HSPK/mm")!) {
                    Label("Source on GitHub", systemImage: "arrow.up.right.square")
                }
            }
        }
        .navigationTitle("Settings")
        .onChange(of: apiBaseURL) { _, _ in savedURL = false }
        .task { await loadLibrary() }
        .refreshable { await loadLibrary() }
        #if os(iOS)
        .formStyle(.grouped)
        #endif
    }

    @ViewBuilder
    private var librarySection: some View {
        Section("Library") {
            if loadingLibrary && currentLibrary == nil {
                ProgressView()
            } else if let cur = currentLibrary {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Label("Active", systemImage: "checkmark.circle.fill")
                            .labelStyle(.iconOnly)
                            .foregroundStyle(.green)
                        Text(cur.name).font(.body.weight(.semibold))
                    }
                    Text(cur.dbPath)
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                }
                .padding(.vertical, 2)
            }

            if let err = libraryError {
                Text(err).font(.caption).foregroundStyle(.red)
            }

            if !recentLibraries.isEmpty {
                ForEach(recentLibraries.filter { $0.dbPath != currentLibrary?.dbPath }) { lib in
                    Button {
                        Task { await switchTo(lib.dbPath) }
                    } label: {
                        HStack {
                            Image(systemName: "folder")
                            VStack(alignment: .leading, spacing: 1) {
                                Text(lib.name).font(.body)
                                Text(lib.dbPath).font(.caption2).foregroundStyle(.secondary).lineLimit(1)
                            }
                            Spacer()
                        }
                    }
                    .disabled(switching)
                    .buttonStyle(.plain)
                }
            }

            HStack {
                TextField("Switch to /path/to/library", text: $newLibraryPath)
                    #if os(iOS)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    #endif
                if switching { ProgressView().controlSize(.small) }
                Button("Switch") {
                    Task { await switchTo(newLibraryPath) }
                }
                .buttonStyle(.borderless)
                .disabled(newLibraryPath.trimmingCharacters(in: .whitespaces).isEmpty || switching)
            }
        }
    }

    private var version: String {
        let v = Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "?"
        let b = Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "?"
        return "\(v) (\(b))"
    }

    private func loadLibrary() async {
        loadingLibrary = true
        libraryError = nil
        defer { loadingLibrary = false }
        do {
            async let cur = libraryRepo.current()
            async let rec = libraryRepo.recent()
            self.currentLibrary = try await cur
            self.recentLibraries = (try await rec)
        } catch {
            self.libraryError = error.localizedDescription
        }
    }

    private func switchTo(_ path: String) async {
        let trimmed = path.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return }
        switching = true
        libraryError = nil
        defer { switching = false }
        do {
            let res = try await libraryRepo.switchTo(dbPath: trimmed)
            currentLibrary = LibraryInfo(dbPath: res.dbPath, name: res.name)
            newLibraryPath = ""
            await loadLibrary()
        } catch {
            self.libraryError = error.localizedDescription
        }
    }
}

#Preview {
    NavigationStack { SettingsView() }
        .environment(AuthStore())
}
