import SwiftUI
import MapKit

/// Shows every media item with GPS coordinates on a map. Uses the dedicated
/// `/api/geo` endpoint that returns up to 2,000 markers in a single query
/// (no client-side pagination). Tap a pin to open the viewer.
struct MapView: View {
    @State private var points: [GeoPoint] = []
    @State private var loading = false
    @State private var error: String?
    @State private var loadedAll = false
    @State private var selectedId: Int?
    @State private var cameraPosition: MapCameraPosition = .automatic
    @State private var libraryStore = MediaQueryStore()

    private let statsRepo = StatsRepository.shared

    var body: some View {
        ZStack {
            map
            if points.isEmpty && loading {
                ProgressView("Loading map…")
                    .padding(20)
                    .background(.regularMaterial, in: .rect(cornerRadius: 12))
            } else if points.isEmpty, let error {
                EmptyState(
                    systemImage: "exclamationmark.triangle",
                    title: "Couldn’t load locations",
                    message: error,
                    actionLabel: "Retry",
                    action: { Task { await loadAll() } },
                )
            } else if points.isEmpty {
                EmptyState(
                    systemImage: "map",
                    title: "No location data",
                    message: "Items with GPS coordinates show up here.",
                    actionLabel: nil,
                    action: nil,
                )
            }
        }
        .navigationTitle("Map")
        #if os(iOS)
        .navigationBarTitleDisplayMode(.inline)
        #endif
        .toolbar {
            ToolbarItem(placement: .primaryAction) {
                if loading {
                    ProgressView().controlSize(.small)
                } else {
                    Button { Task { await loadAll(force: true) } } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                }
            }
        }
        .task { if points.isEmpty { await loadAll() } }
        .fullScreenCoverIfAvailable(item: Binding(
            get: { selectedId.map { OpenedPoint(id: $0) } },
            set: { selectedId = $0?.id },
        )) { opened in
            MediaDetailView(
                store: detailStore(),
                startId: opened.id,
                onClose: { selectedId = nil },
                onDelete: { id in
                    points.removeAll { $0.id == id }
                    selectedId = nil
                },
            )
        }
    }

    /// Synthesises a minimal Media[] from current points and feeds the
    /// existing MediaQueryStore so the viewer can swipe across pins.
    /// MediaDetailView fetches full detail per item on demand.
    private func detailStore() -> MediaQueryStore {
        libraryStore.replace(with: points.map(syntheticMedia))
        return libraryStore
    }

    private func syntheticMedia(_ p: GeoPoint) -> Media {
        Media(
            id: p.id, filename: p.filename, extension_: "",
            mediaType: p.mediaType, fileSize: 0, rating: 0,
            width: nil, height: nil, dateTaken: p.date,
            cameraModel: nil, duration: nil,
            gpsLat: p.lat, gpsLon: p.lon,
            locationLabel: p.city, locationCity: p.city, locationCountry: nil,
            deletedAt: nil,
        )
    }

    @ViewBuilder
    private var map: some View {
        Map(position: $cameraPosition) {
            ForEach(points) { p in
                Annotation(p.city ?? "", coordinate: CLLocationCoordinate2D(latitude: p.lat, longitude: p.lon)) {
                    MapPinThumb(id: p.id, filename: p.filename)
                        .onTapGesture { selectedId = p.id }
                }
            }
        }
        .mapControls {
            MapCompass()
            MapScaleView()
        }
    }

    private func loadAll(force: Bool = false) async {
        if force {
            points = []
            loadedAll = false
        }
        guard !loadedAll, !loading else { return }
        loading = true
        defer { loading = false }
        error = nil
        do {
            points = try await statsRepo.geo(limit: 2000)
            loadedAll = true
            recenter()
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func recenter() {
        guard !points.isEmpty else { return }
        let lats = points.map(\.lat)
        let lons = points.map(\.lon)
        guard let minLat = lats.min(), let maxLat = lats.max(),
              let minLon = lons.min(), let maxLon = lons.max() else { return }
        let center = CLLocationCoordinate2D(
            latitude: (minLat + maxLat) / 2,
            longitude: (minLon + maxLon) / 2,
        )
        let span = MKCoordinateSpan(
            latitudeDelta: max(0.01, (maxLat - minLat) * 1.4),
            longitudeDelta: max(0.01, (maxLon - minLon) * 1.4),
        )
        cameraPosition = .region(MKCoordinateRegion(center: center, span: span))
    }
}

private struct OpenedPoint: Identifiable, Hashable {
    let id: Int
}

private struct MapPinThumb: View {
    let id: Int
    let filename: String

    var body: some View {
        AuthAsyncImage(url: MediaRepository.shared.thumbnailURL(for: id, size: "sm"))
            .frame(width: 36, height: 36)
            .clipShape(.rect(cornerRadius: 6))
            .overlay(RoundedRectangle(cornerRadius: 6).stroke(.white, lineWidth: 2))
            .shadow(radius: 2, y: 1)
            .accessibilityLabel(filename)
    }
}
