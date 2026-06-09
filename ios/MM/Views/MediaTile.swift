import SwiftUI

struct MediaTile: View {
    let item: Media
    var selectionMode: Bool = false
    var selected: Bool = false

    private let repo = MediaRepository.shared

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            AuthAsyncImage(url: repo.thumbnailURL(for: item.id, size: "md"))
                .aspectRatio(1, contentMode: .fill)
                .scaleEffect(selectionMode && selected ? 0.92 : 1)
                .animation(.easeOut(duration: 0.15), value: selected)
                .clipShape(.rect(cornerRadius: selectionMode && selected ? 8 : 4))

            if item.isVideo && !selectionMode {
                Label(formatDuration(item.duration), systemImage: "play.fill")
                    .labelStyle(.titleAndIcon)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(.white)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(.black.opacity(0.5), in: .capsule)
                    .padding(6)
            }

            if selectionMode {
                SelectionIndicator(selected: selected)
                    .padding(6)
            }
        }
        .contentShape(.rect)
    }

    private func formatDuration(_ seconds: Double?) -> String {
        guard let s = seconds, s > 0 else { return "Video" }
        let m = Int(s) / 60
        let rem = Int(s) % 60
        return String(format: "%d:%02d", m, rem)
    }
}

private struct SelectionIndicator: View {
    let selected: Bool
    var body: some View {
        ZStack {
            Circle()
                .fill(selected ? Color.accentColor : .black.opacity(0.3))
                .frame(width: 22, height: 22)
            Circle()
                .stroke(selected ? Color.clear : .white.opacity(0.85), lineWidth: 2)
                .frame(width: 22, height: 22)
            if selected {
                Image(systemName: "checkmark")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(.white)
            }
        }
    }
}
