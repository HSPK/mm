import Foundation
import Observation

@MainActor
@Observable
final class SelectionStore {
    private(set) var isActive = false
    private(set) var selected: Set<Int> = []

    var count: Int { selected.count }

    func enter(with id: Int? = nil) {
        isActive = true
        selected = id.map { [$0] } ?? []
    }

    func exit() {
        isActive = false
        selected = []
    }

    func toggle(_ id: Int) {
        if selected.contains(id) {
            selected.remove(id)
            if selected.isEmpty { isActive = false }
        } else {
            selected.insert(id)
        }
    }

    func selectAll(in ids: [Int]) {
        isActive = true
        selected = Set(ids)
    }

    func prune(removed ids: [Int]) {
        for id in ids { selected.remove(id) }
        if selected.isEmpty { isActive = false }
    }
}
