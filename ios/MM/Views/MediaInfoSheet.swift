import SwiftUI

/// Sheet shown by the viewer when the "info" action is tapped. Shows
/// metadata, lets the user set rating and add/remove tags, and updates the
/// shared MediaQueryStore so the grid stays in sync.
struct MediaInfoSheet: View {
    let mediaId: Int
    var store: MediaQueryStore

    @Environment(\.dismiss) private var dismiss
    @State private var detail: MediaDetail?
    @State private var loading = false
    @State private var loadError: String?
    @State private var tagDraft: String = ""
    @State private var addingTag = false
    @State private var error: String?
    @State private var editing = false
    @State private var savingEdit = false
    @State private var edit = EditDraft()

    private let repo = MediaRepository.shared

    var body: some View {
        NavigationStack {
            Group {
                if loading {
                    ProgressView().controlSize(.large)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let detail {
                    detailBody(detail: detail)
                } else if let err = loadError {
                    EmptyState(
                        systemImage: "exclamationmark.triangle",
                        title: "Couldn’t load details",
                        message: err,
                        actionLabel: "Retry",
                        action: { Task { await load() } },
                    )
                } else {
                    Text("No details").foregroundStyle(.secondary)
                }
            }
            .navigationTitle(editing ? "Edit details" : "Details")
            #if os(iOS)
            .navigationBarTitleDisplayMode(.inline)
            #endif
            .toolbar {
                if editing {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") { cancelEdit() }
                            .disabled(savingEdit)
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        if savingEdit {
                            ProgressView().controlSize(.small)
                        } else {
                            Button("Save") { Task { await saveEdit() } }
                                .disabled(!edit.hasChanges)
                        }
                    }
                } else {
                    if detail != nil {
                        ToolbarItem(placement: .cancellationAction) {
                            Button("Edit") { beginEdit() }
                        }
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Done") { dismiss() }
                    }
                }
            }
            .overlay(alignment: .bottom) {
                if let error {
                    Label(error, systemImage: "exclamationmark.triangle.fill")
                        .padding(.horizontal, 14).padding(.vertical, 10)
                        .background(.regularMaterial, in: .capsule)
                        .padding(.bottom, 24)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
        }
        .task { await load() }
    }

    @ViewBuilder
    private func detailBody(detail: MediaDetail) -> some View {
        Form {
            Section {
                LabeledContent("Filename") { Text(detail.filename).lineLimit(2) }
                LabeledContent("Size") { Text(humanSize(detail.fileSize)) }
                LabeledContent("Type") { Text(detail.mediaType.capitalized) }
                if let s = detail.scannedAt, let d = parseISO(s) {
                    LabeledContent("Scanned") { Text(d, style: .date) }
                }
            }

            if !editing {
                Section("Rating") {
                    StarRatingPicker(value: Binding(
                        get: { detail.rating },
                        set: { rating in Task { await setRating(rating) } },
                    ))
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.vertical, 4)
                }
            }

            if editing {
                metadataEditSections()
            } else if let md = detail.metadata {
                metadataSections(md)
            }

            if !editing {
                Section("Tags") {
                    if detail.tags.isEmpty && tagDraft.isEmpty {
                        Text("No tags").foregroundStyle(.secondary).italic()
                    }
                    if !detail.tags.isEmpty {
                        FlowLayout(spacing: 6) {
                            ForEach(detail.tags, id: \.name) { tag in
                                TagPill(name: tag.name) {
                                    Task { await removeTag(tag.name) }
                                }
                            }
                        }
                    }
                    HStack {
                        TextField("Add tag", text: $tagDraft)
                            #if os(iOS)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            #endif
                            .onSubmit { Task { await addTag() } }
                        if addingTag { ProgressView().controlSize(.small) }
                        Button("Add") { Task { await addTag() } }
                            .disabled(tagDraft.trimmingCharacters(in: .whitespaces).isEmpty || addingTag)
                            .buttonStyle(.borderless)
                    }
                }
            }

            Section("File path") {
                Text(detail.path)
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            }
        }
        #if os(iOS)
        .formStyle(.grouped)
        #endif
    }

    @ViewBuilder
    private func metadataSections(_ md: MediaMetadata) -> some View {
        let dateString = md.dateTaken.flatMap(parseISO)
        if dateString != nil || md.cameraModel != nil || md.lensModel != nil {
            Section("Capture") {
                if let date = dateString {
                    LabeledContent("Date") { Text(date, style: .date) + Text("  ") + Text(date, style: .time) }
                }
                if let camera = md.cameraModel, !camera.isEmpty {
                    LabeledContent("Camera") {
                        VStack(alignment: .trailing, spacing: 1) {
                            if let make = md.cameraMake, !make.isEmpty { Text(make).font(.caption2).foregroundStyle(.secondary) }
                            Text(camera)
                        }
                    }
                }
                if let lens = md.lensModel, !lens.isEmpty {
                    LabeledContent("Lens") { Text(lens) }
                }
                if let exp = exposureString(md) {
                    LabeledContent("Exposure") { Text(exp) }
                }
            }
        }

        if let w = md.width, let h = md.height, w > 0 && h > 0 {
            Section("Dimensions") {
                LabeledContent("Pixels") { Text("\(w) × \(h)") }
                if let dur = md.duration, dur > 0 {
                    LabeledContent("Duration") { Text(formatDuration(dur)) }
                }
            }
        }

        if let lat = md.gpsLat, let lon = md.gpsLon {
            Section("Location") {
                if let name = md.locationLabel ?? md.locationCity {
                    LabeledContent("Place") { Text(name).lineLimit(2) }
                }
                if let country = md.locationCountry {
                    LabeledContent("Country") { Text(country) }
                }
                LabeledContent("Coordinates") {
                    Text(String(format: "%.5f, %.5f", lat, lon))
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                }
            }
        }
    }

    // MARK: - Edit form

    @ViewBuilder
    private func metadataEditSections() -> some View {
        Section("Capture") {
            DatePicker(
                "Date taken",
                selection: Binding(
                    get: { edit.dateTaken ?? Date() },
                    set: { edit.dateTaken = $0 },
                ),
                displayedComponents: [.date, .hourAndMinute],
            )
            TextField("Camera make", text: $edit.cameraMake)
                #if os(iOS)
                .textInputAutocapitalization(.words)
                #endif
            TextField("Camera model", text: $edit.cameraModel)
            TextField("Lens", text: $edit.lensModel)
        }
        Section("Exposure") {
            HStack {
                Text("Focal length")
                Spacer()
                TextField("mm", text: $edit.focalLength)
                    #if os(iOS)
                    .keyboardType(.decimalPad)
                    #endif
                    .multilineTextAlignment(.trailing)
                    .frame(maxWidth: 120)
            }
            HStack {
                Text("Aperture")
                Spacer()
                TextField("ƒ/1.8", text: $edit.aperture)
                    #if os(iOS)
                    .keyboardType(.decimalPad)
                    #endif
                    .multilineTextAlignment(.trailing)
                    .frame(maxWidth: 120)
            }
            HStack {
                Text("Shutter speed")
                Spacer()
                TextField("1/250", text: $edit.shutterSpeed)
                    .multilineTextAlignment(.trailing)
                    .frame(maxWidth: 120)
            }
            HStack {
                Text("ISO")
                Spacer()
                TextField("100", text: $edit.iso)
                    #if os(iOS)
                    .keyboardType(.numberPad)
                    #endif
                    .multilineTextAlignment(.trailing)
                    .frame(maxWidth: 120)
            }
        }
        Section("Location") {
            TextField("Place", text: $edit.locationLabel)
            TextField("City", text: $edit.locationCity)
            TextField("Country", text: $edit.locationCountry)
            HStack {
                Text("Latitude")
                Spacer()
                TextField("0.00000", text: $edit.gpsLat)
                    #if os(iOS)
                    .keyboardType(.numbersAndPunctuation)
                    #endif
                    .multilineTextAlignment(.trailing)
                    .frame(maxWidth: 140)
            }
            HStack {
                Text("Longitude")
                Spacer()
                TextField("0.00000", text: $edit.gpsLon)
                    #if os(iOS)
                    .keyboardType(.numbersAndPunctuation)
                    #endif
                    .multilineTextAlignment(.trailing)
                    .frame(maxWidth: 140)
            }
        }
    }

    private func beginEdit() {
        guard let detail else { return }
        edit = EditDraft(detail: detail, parseISO: parseISO)
        withAnimation { editing = true }
    }

    private func cancelEdit() {
        withAnimation {
            editing = false
            edit = EditDraft()
        }
    }

    private func saveEdit() async {
        let patch = edit.buildPatch()
        guard !patch.isEmpty else { cancelEdit(); return }
        savingEdit = true
        defer { savingEdit = false }
        do {
            let updated = try await repo.updateMetadata(id: mediaId, patch: patch)
            detail = updated
            applyMetadataToGridStore(updated)
            withAnimation { editing = false }
        } catch {
            self.error = error.localizedDescription
            scheduleErrorDismiss()
        }
    }

    /// Keep the grid item in sync so users see the updated date/location
    /// without reloading the whole page.
    private func applyMetadataToGridStore(_ d: MediaDetail) {
        store.update(id: mediaId) { item in
            Media(
                id: item.id,
                filename: item.filename,
                extension_: item.extension_,
                mediaType: item.mediaType,
                fileSize: item.fileSize,
                rating: d.rating,
                width: d.metadata?.width ?? item.width,
                height: d.metadata?.height ?? item.height,
                dateTaken: d.metadata?.dateTaken ?? item.dateTaken,
                cameraModel: d.metadata?.cameraModel ?? item.cameraModel,
                duration: d.metadata?.duration ?? item.duration,
                gpsLat: d.metadata?.gpsLat ?? item.gpsLat,
                gpsLon: d.metadata?.gpsLon ?? item.gpsLon,
                locationLabel: d.metadata?.locationLabel ?? item.locationLabel,
                locationCity: d.metadata?.locationCity ?? item.locationCity,
                locationCountry: d.metadata?.locationCountry ?? item.locationCountry,
                deletedAt: item.deletedAt,
            )
        }
    }

    // MARK: - Actions

    private func load() async {
        loading = true
        loadError = nil
        defer { loading = false }
        do {
            detail = try await repo.get(id: mediaId)
        } catch {
            loadError = error.localizedDescription
        }
    }

    private func setRating(_ rating: Int) async {
        do {
            let res = try await repo.setRating(id: mediaId, rating: rating)
            detail = detail.map { d in
                MediaDetail(
                    id: d.id, path: d.path, filename: d.filename, extension_: d.extension_,
                    mediaType: d.mediaType, fileSize: d.fileSize, fileHash: d.fileHash,
                    rating: res.rating, scannedAt: d.scannedAt, metadata: d.metadata, tags: d.tags,
                )
            }
            store.update(id: mediaId) { item in
                Media(
                    id: item.id, filename: item.filename, extension_: item.extension_,
                    mediaType: item.mediaType, fileSize: item.fileSize, rating: res.rating,
                    width: item.width, height: item.height, dateTaken: item.dateTaken,
                    cameraModel: item.cameraModel, duration: item.duration,
                    gpsLat: item.gpsLat, gpsLon: item.gpsLon,
                    locationLabel: item.locationLabel, locationCity: item.locationCity,
                    locationCountry: item.locationCountry, deletedAt: item.deletedAt,
                )
            }
        } catch {
            self.error = error.localizedDescription
            scheduleErrorDismiss()
        }
    }

    private func addTag() async {
        let name = tagDraft.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty, !addingTag else { return }
        addingTag = true
        defer { addingTag = false }
        do {
            try await repo.addTags(id: mediaId, tags: [name])
            tagDraft = ""
            await load()
        } catch {
            self.error = error.localizedDescription
            scheduleErrorDismiss()
        }
    }

    private func removeTag(_ name: String) async {
        do {
            try await repo.removeTag(id: mediaId, name: name)
            await load()
        } catch {
            self.error = error.localizedDescription
            scheduleErrorDismiss()
        }
    }

    private func scheduleErrorDismiss() {
        Task {
            try? await Task.sleep(for: .seconds(2.5))
            withAnimation { error = nil }
        }
    }

    // MARK: - Formatting

    private func humanSize(_ bytes: Int) -> String {
        let f = ByteCountFormatter()
        f.allowedUnits = [.useAll]
        f.countStyle = .file
        return f.string(fromByteCount: Int64(bytes))
    }

    private func parseISO(_ s: String) -> Date? {
        if let d = ISO8601DateFormatter().date(from: s) { return d }
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let d = f.date(from: s) { return d }
        let plain = DateFormatter()
        plain.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        return plain.date(from: s)
    }

    private func exposureString(_ md: MediaMetadata) -> String? {
        var parts: [String] = []
        if let focal = md.focalLength, focal > 0 { parts.append(String(format: "%.0fmm", focal)) }
        if let ap = md.aperture, ap > 0 { parts.append(String(format: "ƒ/%.1f", ap)) }
        if let iso = md.iso, iso > 0 { parts.append("ISO \(iso)") }
        if let speed = md.shutterSpeed, !speed.isEmpty { parts.append("\(speed)s") }
        return parts.isEmpty ? nil : parts.joined(separator: " · ")
    }

    private func formatDuration(_ seconds: Double) -> String {
        let total = Int(seconds)
        if total < 3600 {
            return String(format: "%d:%02d", total / 60, total % 60)
        }
        return String(format: "%d:%02d:%02d", total / 3600, (total / 60) % 60, total % 60)
    }
}

// MARK: - Edit draft (text-bound form state)

private struct EditDraft: Equatable {
    var dateTaken: Date?
    var cameraMake: String = ""
    var cameraModel: String = ""
    var lensModel: String = ""
    var focalLength: String = ""
    var aperture: String = ""
    var shutterSpeed: String = ""
    var iso: String = ""
    var gpsLat: String = ""
    var gpsLon: String = ""
    var locationLabel: String = ""
    var locationCity: String = ""
    var locationCountry: String = ""

    fileprivate var original: Snapshot = Snapshot()

    init() {}

    init(detail: MediaDetail, parseISO: (String) -> Date?) {
        let md = detail.metadata
        dateTaken = md?.dateTaken.flatMap { parseISO($0) }
        cameraMake = md?.cameraMake ?? ""
        cameraModel = md?.cameraModel ?? ""
        lensModel = md?.lensModel ?? ""
        focalLength = md?.focalLength.map { String(format: "%g", $0) } ?? ""
        aperture = md?.aperture.map { String(format: "%g", $0) } ?? ""
        shutterSpeed = md?.shutterSpeed ?? ""
        iso = md?.iso.map { String($0) } ?? ""
        gpsLat = md?.gpsLat.map { String($0) } ?? ""
        gpsLon = md?.gpsLon.map { String($0) } ?? ""
        locationLabel = md?.locationLabel ?? ""
        locationCity = md?.locationCity ?? ""
        locationCountry = md?.locationCountry ?? ""
        original = Snapshot(
            dateTaken: dateTaken,
            cameraMake: cameraMake, cameraModel: cameraModel, lensModel: lensModel,
            focalLength: focalLength, aperture: aperture, shutterSpeed: shutterSpeed, iso: iso,
            gpsLat: gpsLat, gpsLon: gpsLon,
            locationLabel: locationLabel, locationCity: locationCity, locationCountry: locationCountry,
        )
    }

    var hasChanges: Bool {
        dateTaken != original.dateTaken
            || cameraMake != original.cameraMake || cameraModel != original.cameraModel
            || lensModel != original.lensModel
            || focalLength != original.focalLength || aperture != original.aperture
            || shutterSpeed != original.shutterSpeed || iso != original.iso
            || gpsLat != original.gpsLat || gpsLon != original.gpsLon
            || locationLabel != original.locationLabel
            || locationCity != original.locationCity
            || locationCountry != original.locationCountry
    }

    func buildPatch() -> MetadataPatch {
        var p = MetadataPatch()
        if dateTaken != original.dateTaken { p.dateTaken = dateTaken }
        if cameraMake != original.cameraMake { p.cameraMake = cameraMake }
        if cameraModel != original.cameraModel { p.cameraModel = cameraModel }
        if lensModel != original.lensModel { p.lensModel = lensModel }
        if focalLength != original.focalLength { p.focalLength = Double(focalLength) ?? 0 }
        if aperture != original.aperture { p.aperture = Double(aperture) ?? 0 }
        if shutterSpeed != original.shutterSpeed { p.shutterSpeed = shutterSpeed }
        if iso != original.iso { p.iso = Int(iso) ?? 0 }
        if gpsLat != original.gpsLat { p.gpsLat = Double(gpsLat) ?? 0 }
        if gpsLon != original.gpsLon { p.gpsLon = Double(gpsLon) ?? 0 }
        if locationLabel != original.locationLabel { p.locationLabel = locationLabel }
        if locationCity != original.locationCity { p.locationCity = locationCity }
        if locationCountry != original.locationCountry { p.locationCountry = locationCountry }
        return p
    }

    struct Snapshot: Equatable {
        var dateTaken: Date?
        var cameraMake: String = ""
        var cameraModel: String = ""
        var lensModel: String = ""
        var focalLength: String = ""
        var aperture: String = ""
        var shutterSpeed: String = ""
        var iso: String = ""
        var gpsLat: String = ""
        var gpsLon: String = ""
        var locationLabel: String = ""
        var locationCity: String = ""
        var locationCountry: String = ""
    }
}

// MARK: - Interactive star rating

struct StarRatingPicker: View {
    @Binding var value: Int
    var max: Int = 5
    var size: CGFloat = 28
    @State private var hover: Int? = nil

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<max, id: \.self) { i in
                let target = i + 1
                let active = (hover ?? value) >= target
                Image(systemName: active ? "star.fill" : "star")
                    .font(.system(size: size))
                    .foregroundStyle(active ? .yellow : .secondary.opacity(0.35))
                    .contentShape(.rect)
                    .onTapGesture { value = (value == target ? 0 : target) }
                    .onHover { isHover in hover = isHover ? target : nil }
                    .accessibilityLabel("Rate \(target) star\(target == 1 ? "" : "s")")
            }
        }
    }
}

// MARK: - Tag pill

private struct TagPill: View {
    let name: String
    let onRemove: () -> Void
    @State private var removing = false

    var body: some View {
        HStack(spacing: 4) {
            Text(name)
                .font(.caption.weight(.medium))
            Button {
                removing = true
                onRemove()
            } label: {
                if removing {
                    ProgressView().controlSize(.mini)
                } else {
                    Image(systemName: "xmark")
                        .font(.caption2.weight(.bold))
                }
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 10).padding(.vertical, 5)
        .background(.purple.opacity(0.15), in: .capsule)
        .overlay(Capsule().stroke(.purple.opacity(0.35), lineWidth: 1))
        .foregroundStyle(.purple)
    }
}

// MARK: - Minimal flow layout (wraps tag pills)

struct FlowLayout: Layout {
    var spacing: CGFloat = 6

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var x: CGFloat = 0
        var y: CGFloat = 0
        var lineHeight: CGFloat = 0
        var maxX: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > width {
                x = 0
                y += lineHeight + spacing
                lineHeight = 0
            }
            x += size.width + spacing
            lineHeight = max(lineHeight, size.height)
            maxX = max(maxX, x - spacing)
        }
        return CGSize(width: maxX, height: y + lineHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x: CGFloat = bounds.minX
        var y: CGFloat = bounds.minY
        var lineHeight: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x + size.width > bounds.maxX {
                x = bounds.minX
                y += lineHeight + spacing
                lineHeight = 0
            }
            subview.place(at: CGPoint(x: x, y: y), proposal: ProposedViewSize(size))
            x += size.width + spacing
            lineHeight = max(lineHeight, size.height)
        }
    }
}
