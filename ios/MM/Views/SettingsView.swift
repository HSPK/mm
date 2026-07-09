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

struct StatusBarSettingsView: View {
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
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                header
                accountCard
                serverCard
                libraryCard
                aboutCard
            }
            .padding(16)
        }
        .background(Color.clear)
        .task { await loadLibrary() }
        .onChange(of: apiBaseURL) { _, _ in savedURL = false }
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 3) {
                Text("MM")
                    .font(.title3.weight(.semibold))
                Text("Quick Settings")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Image(systemName: "photo.stack")
                .font(.title2)
                .foregroundStyle(.tint)
                .frame(width: 36, height: 36)
                .background(.tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 10))
        }
    }

    @ViewBuilder
    private var accountCard: some View {
        settingsCard("Account", systemImage: "person.crop.circle") {
            if let user = auth.user {
                HStack(spacing: 12) {
                    Text(user.initial)
                        .font(.title3.weight(.bold))
                        .foregroundStyle(.tint)
                        .frame(width: 40, height: 40)
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

                Button(role: .destructive, action: auth.signOut) {
                    Label("Sign out", systemImage: "rectangle.portrait.and.arrow.right")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            } else {
                Text("Not signed in")
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var serverCard: some View {
        settingsCard("Server", systemImage: "network") {
            TextField("API base URL", text: $apiBaseURL)
                .textFieldStyle(.roundedBorder)

            Button {
                if let url = URL(string: apiBaseURL), url.scheme != nil {
                    AppConfig.setAPIBaseURL(url)
                    savedURL = true
                }
            } label: {
                Label(savedURL ? "Saved" : "Save server URL", systemImage: savedURL ? "checkmark.circle.fill" : "square.and.arrow.down")
                    .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .disabled(apiBaseURL.isEmpty)
        }
    }

    private var libraryCard: some View {
        settingsCard("Library", systemImage: "externaldrive") {
            if loadingLibrary && currentLibrary == nil {
                ProgressView()
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else if let cur = currentLibrary {
                VStack(alignment: .leading, spacing: 4) {
                    Text(cur.name)
                        .font(.body.weight(.semibold))
                    Text(cur.dbPath)
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                        .textSelection(.enabled)
                }
            }

            if let err = libraryError {
                Text(err)
                    .font(.caption)
                    .foregroundStyle(.red)
            }

            if !recentLibraries.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(recentLibraries.filter { $0.dbPath != currentLibrary?.dbPath }.prefix(3)) { lib in
                        Button {
                            Task { await switchTo(lib.dbPath) }
                        } label: {
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(lib.name)
                                        .foregroundStyle(.primary)
                                    Text(lib.dbPath)
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                                Spacer()
                                Image(systemName: "arrow.right.circle")
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .buttonStyle(.plain)
                        .disabled(switching)
                    }
                }
            }

            HStack(spacing: 8) {
                TextField("Switch to /path/to/library", text: $newLibraryPath)
                    .textFieldStyle(.roundedBorder)
                if switching {
                    ProgressView().controlSize(.small)
                }
            }

            Button("Switch Library") {
                Task { await switchTo(newLibraryPath) }
            }
            .buttonStyle(.bordered)
            .disabled(newLibraryPath.trimmingCharacters(in: .whitespaces).isEmpty || switching)
        }
    }

    private var aboutCard: some View {
        settingsCard("About", systemImage: "info.circle") {
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

    private func settingsCard<Content: View>(
        _ title: String,
        systemImage: String,
        @ViewBuilder content: () -> Content,
    ) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(title, systemImage: systemImage)
                .font(.headline)
            content()
        }
        .padding(14)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
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
            currentLibrary = try await cur
            recentLibraries = try await rec
        } catch {
            libraryError = error.localizedDescription
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
            libraryError = error.localizedDescription
        }
    }
}

#Preview {
    NavigationStack { SettingsView() }
        .environment(AuthStore())
}
