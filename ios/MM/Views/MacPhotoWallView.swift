#if os(macOS)
import AppKit
import SwiftUI

struct MacPhotoWallView: NSViewRepresentable {
    let items: [Media]
    let inTrash: Bool
    let onOpen: (Media) -> Void
    let onLoadMore: (Media) -> Void
    let onAddToAlbum: (Media) -> Void
    let onMoveToTrash: (Media) -> Void
    let onRestore: (Media) -> Void
    let onDeletePermanently: (Media) -> Void

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    func makeNSView(context: Context) -> NSScrollView {
        let layout = NSCollectionViewFlowLayout()
        layout.itemSize = NSSize(width: 118, height: 118)
        layout.minimumInteritemSpacing = 2
        layout.minimumLineSpacing = 2
        layout.sectionInset = NSEdgeInsets(top: 0, left: 18, bottom: 24, right: 18)

        let collectionView = PhotoCollectionView()
        collectionView.collectionViewLayout = layout
        collectionView.backgroundColors = [.clear]
        collectionView.isSelectable = true
        collectionView.allowsMultipleSelection = false
        collectionView.dataSource = context.coordinator
        collectionView.delegate = context.coordinator
        collectionView.photoCoordinator = context.coordinator
        collectionView.register(MacPhotoItem.self, forItemWithIdentifier: MacPhotoItem.reuseIdentifier)

        let scrollView = NSScrollView()
        scrollView.documentView = collectionView
        scrollView.hasVerticalScroller = true
        scrollView.drawsBackground = false
        scrollView.autohidesScrollers = true
        context.coordinator.collectionView = collectionView
        return scrollView
    }

    func updateNSView(_ scrollView: NSScrollView, context: Context) {
        context.coordinator.parent = self
        context.coordinator.items = items
        if let collectionView = scrollView.documentView as? NSCollectionView {
            collectionView.reloadData()
            let urls = items.prefix(48).map {
                MediaRepository.shared.thumbnailURL(for: $0.id, size: "md")
            }
            Task {
                await MacImagePipeline.shared.prefetch(urls)
            }
        }
    }

    final class Coordinator: NSObject, NSCollectionViewDataSource, NSCollectionViewDelegate {
        var parent: MacPhotoWallView
        var items: [Media]
        weak var collectionView: NSCollectionView?

        init(_ parent: MacPhotoWallView) {
            self.parent = parent
            self.items = parent.items
        }

        func collectionView(_ collectionView: NSCollectionView, numberOfItemsInSection section: Int) -> Int {
            items.count
        }

        func collectionView(
            _ collectionView: NSCollectionView,
            itemForRepresentedObjectAt indexPath: IndexPath,
        ) -> NSCollectionViewItem {
            guard let item = collectionView.makeItem(
                withIdentifier: MacPhotoItem.reuseIdentifier,
                for: indexPath,
            ) as? MacPhotoItem else {
                return NSCollectionViewItem()
            }
            item.configure(with: items[indexPath.item])
            return item
        }

        func collectionView(
            _ collectionView: NSCollectionView,
            willDisplay item: NSCollectionViewItem,
            forRepresentedObjectAt indexPath: IndexPath,
        ) {
            guard indexPath.item >= items.count - 12 else { return }
            parent.onLoadMore(items[indexPath.item])
        }

        func collectionView(_ collectionView: NSCollectionView, didSelectItemsAt indexPaths: Set<IndexPath>) {
            guard let indexPath = indexPaths.first, indexPath.item < items.count else { return }
            collectionView.deselectItems(at: indexPaths)
            parent.onOpen(items[indexPath.item])
        }

        func menu(for indexPath: IndexPath) -> NSMenu? {
            guard indexPath.item < items.count else { return nil }
            let item = items[indexPath.item]
            let menu = NSMenu()
            menu.addItem(menuItem("Open", action: #selector(open(_:)), item: item))

            if parent.inTrash {
                menu.addItem(menuItem("Restore", action: #selector(restore(_:)), item: item))
                menu.addItem(NSMenuItem.separator())
                menu.addItem(menuItem("Delete Permanently", action: #selector(deletePermanently(_:)), item: item))
            } else {
                menu.addItem(menuItem("Add to Album", action: #selector(addToAlbum(_:)), item: item))
                menu.addItem(NSMenuItem.separator())
                menu.addItem(menuItem("Move to Trash", action: #selector(moveToTrash(_:)), item: item))
            }
            return menu
        }

        private func menuItem(_ title: String, action: Selector, item: Media) -> NSMenuItem {
            let menuItem = NSMenuItem(title: title, action: action, keyEquivalent: "")
            menuItem.target = self
            menuItem.representedObject = item.id
            return menuItem
        }

        private func representedMedia(_ sender: NSMenuItem) -> Media? {
            guard let id = sender.representedObject as? Int else { return nil }
            return items.first { $0.id == id }
        }

        @objc private func open(_ sender: NSMenuItem) {
            guard let item = representedMedia(sender) else { return }
            parent.onOpen(item)
        }

        @objc private func addToAlbum(_ sender: NSMenuItem) {
            guard let item = representedMedia(sender) else { return }
            parent.onAddToAlbum(item)
        }

        @objc private func moveToTrash(_ sender: NSMenuItem) {
            guard let item = representedMedia(sender) else { return }
            parent.onMoveToTrash(item)
        }

        @objc private func restore(_ sender: NSMenuItem) {
            guard let item = representedMedia(sender) else { return }
            parent.onRestore(item)
        }

        @objc private func deletePermanently(_ sender: NSMenuItem) {
            guard let item = representedMedia(sender) else { return }
            parent.onDeletePermanently(item)
        }
    }
}

private final class PhotoCollectionView: NSCollectionView {
    weak var photoCoordinator: MacPhotoWallView.Coordinator?

    override func menu(for event: NSEvent) -> NSMenu? {
        let point = convert(event.locationInWindow, from: nil)
        guard let indexPath = indexPathForItem(at: point) else { return nil }
        return photoCoordinator?.menu(for: indexPath)
    }
}

private final class MacPhotoItem: NSCollectionViewItem {
    static let reuseIdentifier = NSUserInterfaceItemIdentifier("MacPhotoItem")

    private let imageLayer = CALayer()
    private let badgeLayer = CATextLayer()
    private var imageTask: Task<Void, Never>?
    private var representedMediaID: Int?

    override func loadView() {
        view = NSView()
        view.wantsLayer = true
        view.layer?.backgroundColor = NSColor.secondaryLabelColor.withAlphaComponent(0.12).cgColor
        view.layer?.cornerRadius = 2
        view.layer?.masksToBounds = true

        imageLayer.contentsGravity = .resizeAspectFill
        imageLayer.masksToBounds = true
        imageLayer.backgroundColor = NSColor.secondaryLabelColor.withAlphaComponent(0.10).cgColor
        imageLayer.contentsScale = NSScreen.main?.backingScaleFactor ?? 2
        view.layer?.addSublayer(imageLayer)

        badgeLayer.fontSize = 10
        badgeLayer.alignmentMode = .center
        badgeLayer.foregroundColor = NSColor.white.cgColor
        badgeLayer.backgroundColor = NSColor.black.withAlphaComponent(0.55).cgColor
        badgeLayer.cornerRadius = 8
        badgeLayer.masksToBounds = true
        badgeLayer.contentsScale = NSScreen.main?.backingScaleFactor ?? 2
        view.layer?.addSublayer(badgeLayer)
    }

    override func viewDidLayout() {
        super.viewDidLayout()
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        imageLayer.frame = view.bounds
        badgeLayer.frame = CGRect(x: view.bounds.maxX - 48, y: 6, width: 40, height: 18)
        CATransaction.commit()
    }

    override var isSelected: Bool {
        didSet {
            view.layer?.borderWidth = isSelected ? 3 : 0
            view.layer?.borderColor = NSColor.controlAccentColor.cgColor
        }
    }

    override func prepareForReuse() {
        super.prepareForReuse()
        imageTask?.cancel()
        imageTask = nil
        representedMediaID = nil
        imageLayer.contents = nil
        badgeLayer.isHidden = true
    }

    func configure(with media: Media) {
        representedMediaID = media.id
        badgeLayer.isHidden = !media.isVideo
        badgeLayer.string = "▶"

        let url = MediaRepository.shared.thumbnailURL(for: media.id, size: "md")
        imageTask = Task { [weak self] in
            let image = await MacImagePipeline.shared.cachedImage(for: url)
            if let image {
                await MainActor.run { self?.set(image, for: media.id) }
                return
            }
            guard !Task.isCancelled else { return }
            do {
                let loaded = try await MacImagePipeline.shared.image(for: url)
                guard !Task.isCancelled, let loaded else { return }
                await MainActor.run { self?.set(loaded, for: media.id) }
            } catch {
                await MainActor.run { self?.imageLayer.contents = nil }
            }
        }
    }

    @MainActor
    private func set(_ image: NSImage, for mediaID: Int) {
        guard representedMediaID == mediaID else { return }
        imageLayer.contents = image.cgImage(forProposedRect: nil, context: nil, hints: nil)
    }
}
#endif
