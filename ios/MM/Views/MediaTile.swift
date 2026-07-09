import SwiftUI

struct MediaTile: View {
    let item: Media
    var selectionMode: Bool = false
    var selected: Bool = false
    var aspectRatio: CGFloat? = 1

    private let repo = MediaRepository.shared

    var body: some View {
        tileBody
            .modifier(OptionalAspectRatio(aspectRatio: aspectRatio))
            .contentShape(.rect)
    }

    private var tileBody: some View {
        ZStack(alignment: .bottomLeading) {
            AuthAsyncImage(url: repo.thumbnailURL(for: item.id, size: "md"), contentMode: .fill)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .clipped()

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

            #if os(macOS)
            if selected {
                RoundedRectangle(cornerRadius: cornerRadius)
                    .strokeBorder(Color.accentColor, lineWidth: 3)
                    .padding(1.5)
            }
            #endif

            if selectionMode {
                SelectionIndicator(selected: selected)
                    .padding(6)
            }
        }
        #if os(macOS)
        .overlay(
            RoundedRectangle(cornerRadius: cornerRadius)
                .strokeBorder(.primary.opacity(0.08), lineWidth: 0.5)
        )
        #endif
        .scaleEffect(tileScale)
        .animation(.easeOut(duration: 0.14), value: selected)
        .clipShape(.rect(cornerRadius: cornerRadius))
    }

    private var cornerRadius: CGFloat {
        #if os(macOS)
        2
        #else
        selectionMode && selected ? 8 : 4
        #endif
    }

    private var tileScale: CGFloat {
        #if os(macOS)
        selectionMode && selected ? 0.965 : 1
        #else
        selectionMode && selected ? 0.92 : 1
        #endif
    }

    private func formatDuration(_ seconds: Double?) -> String {
        guard let s = seconds, s > 0 else { return "Video" }
        let m = Int(s) / 60
        let rem = Int(s) % 60
        return String(format: "%d:%02d", m, rem)
    }
}

private struct OptionalAspectRatio: ViewModifier {
    let aspectRatio: CGFloat?

    func body(content: Content) -> some View {
        if let aspectRatio {
            content.aspectRatio(aspectRatio, contentMode: .fit)
        } else {
            content
        }
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
