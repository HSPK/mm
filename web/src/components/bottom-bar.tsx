import { useCallback, useEffect, type MutableRefObject, type RefObject } from "react"
import { cn } from "@/lib/utils"
import { useMediaQueryStore } from "@/stores/media-query"
import { useSelectionStore } from "@/stores/media-selection"
import { useAlbumActions } from "@/hooks/use-album-actions"
import { useTrashActions } from "@/hooks/use-trash-actions"
import { toast } from "@/stores/toast"
import { AlbumPickerPopover } from "@/components/bottom-bar/album-picker-popover"
import { NavTabsBar } from "@/components/bottom-bar/nav-tabs-bar"
import { SelectionActionBar } from "@/components/bottom-bar/selection-action-bar"
import { TrashActionBar } from "@/components/bottom-bar/trash-action-bar"

interface BottomBarProps {
    isTabRoute: boolean
    navVisible: boolean
    navRef: RefObject<HTMLElement | null>
    itemRefs: MutableRefObject<(HTMLAnchorElement | null)[]>
    indicator: { left: number; width: number }
}

export function BottomBar({ isTabRoute, navVisible, navRef, itemRefs, indicator }: BottomBarProps) {
    const items = useMediaQueryStore((s) => s.items)
    const total = useMediaQueryStore((s) => s.total)
    const viewingAlbum = useMediaQueryStore((s) => s.activeLabel)
    const isDeletedView = useMediaQueryStore((s) => s.filters.deleted)
    const resetFilters = useMediaQueryStore((s) => s.resetFilters)

    const { selectionMode, selectedIds, exitSelectionMode, selectAllIds } = useSelectionStore()
    const selectAll = useCallback(
        () => selectAllIds(items.map((i) => i.id)),
        [items, selectAllIds],
    )

    const notify = useCallback((message: string) => toast.error(message), [])

    const albumActions = useAlbumActions({ notify })
    const trashActions = useTrashActions({
        notify,
        onCleanup: () => albumActions.close(),
    })

    useEffect(() => {
        if (!selectionMode) albumActions.close()
    }, [selectionMode, albumActions])

    const handleSelectionDelete = isDeletedView
        ? () => trashActions.handleDeletePermanently([...selectedIds])
        : albumActions.handleDeleteSelected

    const show = isTabRoute && (selectionMode || isDeletedView || (navVisible && !viewingAlbum))

    return (
        <div
            className={cn(
                "fixed bottom-0 left-0 right-0 z-30 transition-transform duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)]",
                show ? "translate-y-0" : "translate-y-full",
            )}
            aria-hidden={!show}
            inert={show ? undefined : true}
            style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
        >
            {selectionMode && <AlbumPickerPopover actions={albumActions} />}

            <div className="flex justify-center px-4 pb-4">
                {selectionMode ? (
                    <SelectionActionBar
                        selectedCount={selectedIds.size}
                        inTrash={isDeletedView}
                        albumPickerOpen={!!albumActions.mode}
                        onCancel={() => { albumActions.close(); exitSelectionMode() }}
                        onSelectAll={selectAll}
                        onToggleAlbumPicker={() => {
                            if (albumActions.mode) albumActions.close()
                            else albumActions.openPicker()
                        }}
                        onDelete={handleSelectionDelete}
                        onRestore={trashActions.handleRestore}
                    />
                ) : isDeletedView ? (
                    <TrashActionBar
                        total={total}
                        onBack={resetFilters}
                        onSelectAll={selectAll}
                        onRestoreAll={trashActions.handleRestore}
                        onEmpty={trashActions.handleEmptyTrash}
                    />
                ) : (
                    <NavTabsBar navRef={navRef} itemRefs={itemRefs} indicator={indicator} />
                )}
            </div>
        </div>
    )
}
