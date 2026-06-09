import SwiftUI

/// Filter editor sheet. Two-way-bound to a Filters value via Binding so the
/// store reacts the moment Apply is tapped (we commit on dismissal).
struct FilterSheet: View {
    @Binding var filters: Filters
    @Environment(\.dismiss) private var dismiss

    @State private var draft: Filters
    @State private var cameras: [CameraInfo] = []

    init(filters: Binding<Filters>) {
        self._filters = filters
        self._draft = State(initialValue: filters.wrappedValue)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Type") {
                    Picker("Media type", selection: $draft.type) {
                        Text("All").tag(Optional<Filters.MediaTypeFilter>.none)
                        ForEach(Filters.MediaTypeFilter.allCases) { kind in
                            Text(kind.label).tag(Optional(kind))
                        }
                    }
                    .pickerStyle(.segmented)
                }

                Section("Date") {
                    Toggle("From date", isOn: dateBinding(\.dateFrom))
                    if draft.dateFrom != nil {
                        DatePicker("Start", selection: Binding(get: { draft.dateFrom ?? Date() }, set: { draft.dateFrom = $0 }), displayedComponents: .date)
                    }
                    Toggle("To date", isOn: dateBinding(\.dateTo))
                    if draft.dateTo != nil {
                        DatePicker("End", selection: Binding(get: { draft.dateTo ?? Date() }, set: { draft.dateTo = $0 }), displayedComponents: .date)
                    }
                }

                Section("Rating") {
                    Stepper(value: Binding(get: { draft.minRating ?? 0 }, set: { draft.minRating = $0 > 0 ? $0 : nil }), in: 0...5) {
                        HStack {
                            Text("Minimum")
                            Spacer()
                            StarsRow(count: draft.minRating ?? 0)
                        }
                    }
                    Toggle("Favorites only (★4+)", isOn: $draft.favoritesOnly)
                }

                Section("Camera") {
                    if cameras.isEmpty {
                        Text("Loading…").foregroundStyle(.secondary)
                    } else {
                        Picker("Camera", selection: cameraSelection) {
                            Text("All").tag(Optional<String>.none)
                            ForEach(cameras, id: \.self) { c in
                                Text("\(c.displayName) (\(c.count))").tag(Optional(c.model.isEmpty ? c.make : c.model))
                            }
                        }
                    }
                }

                Section("Sort") {
                    Picker("Field", selection: $draft.sort) {
                        ForEach(Filters.SortKey.allCases) { s in Text(s.label).tag(s) }
                    }
                    Picker("Order", selection: $draft.order) {
                        Text("Newest first").tag(Filters.SortOrder.descending)
                        Text("Oldest first").tag(Filters.SortOrder.ascending)
                    }
                    .pickerStyle(.segmented)
                }

                Section {
                    Button("Reset all filters", role: .destructive) {
                        draft = Filters()
                    }
                }
            }
            .navigationTitle("Filters")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Apply") {
                        filters = draft
                        dismiss()
                    }
                    .bold()
                }
            }
            .task {
                if cameras.isEmpty {
                    cameras = (try? await CatalogRepository.shared.listCameras()) ?? []
                }
            }
        }
    }

    private var cameraSelection: Binding<String?> {
        Binding(get: { draft.camera }, set: { draft.camera = $0?.isEmpty == true ? nil : $0 })
    }

    private func dateBinding(_ kp: WritableKeyPath<Filters, Date?>) -> Binding<Bool> {
        Binding(
            get: { draft[keyPath: kp] != nil },
            set: { on in
                if on { draft[keyPath: kp] = draft[keyPath: kp] ?? Date() }
                else { draft[keyPath: kp] = nil }
            },
        )
    }
}

struct StarsRow: View {
    let count: Int
    var max: Int = 5
    var size: CGFloat = 14
    var body: some View {
        HStack(spacing: 1) {
            ForEach(0..<max, id: \.self) { i in
                Image(systemName: i < count ? "star.fill" : "star")
                    .font(.system(size: size))
                    .foregroundStyle(i < count ? .yellow : .secondary.opacity(0.4))
            }
        }
    }
}
