import SwiftUI

/// Sheet shown when the user taps "Add to album" from the selection action
/// bar. Lists existing albums + offers a quick-create field.
struct AlbumPickerSheet: View {
    let mediaIds: [Int]
    /// Called with the resolved album id after a successful add.
    let onAdded: (Int) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var albums: [AlbumSummary] = []
    @State private var loading = true
    @State private var error: String?
    @State private var newName = ""
    @State private var working = false

    private let repo = AlbumRepository.shared

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack {
                        TextField("New album name", text: $newName)
                            #if os(iOS)
                            .textInputAutocapitalization(.words)
                            #endif
                            .onSubmit { Task { await createAndAdd() } }
                        Button("Create") { Task { await createAndAdd() } }
                            .buttonStyle(.borderedProminent)
                            .disabled(newName.trimmingCharacters(in: .whitespaces).isEmpty || working)
                    }
                }

                Section("Existing albums") {
                    if loading {
                        ProgressView()
                    } else if let error {
                        Text(error).foregroundStyle(.red)
                    } else if albums.isEmpty {
                        Text("No albums yet").foregroundStyle(.secondary)
                    } else {
                        ForEach(albums) { album in
                            Button {
                                Task { await addTo(album: album) }
                            } label: {
                                HStack {
                                    Image(systemName: "folder")
                                    Text(album.name)
                                    Spacer()
                                    if working { ProgressView().controlSize(.mini) }
                                }
                                .contentShape(.rect)
                            }
                            .disabled(working)
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
            .navigationTitle("Add \(mediaIds.count) to album")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
            }
        }
        .task { await loadAlbums() }
        #if os(macOS)
        .frame(minWidth: 360, minHeight: 420)
        #endif
    }

    private func loadAlbums() async {
        loading = true
        defer { loading = false }
        do {
            albums = try await repo.list()
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func addTo(album: AlbumSummary) async {
        working = true
        defer { working = false }
        do {
            try await repo.addMedia(albumId: album.id, mediaIds: mediaIds)
            onAdded(album.id)
            dismiss()
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func createAndAdd() async {
        let name = newName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }
        working = true
        defer { working = false }
        do {
            let created = try await repo.create(name: name)
            try await repo.addMedia(albumId: created.id, mediaIds: mediaIds)
            onAdded(created.id)
            dismiss()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
