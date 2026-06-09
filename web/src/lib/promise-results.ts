/** Returns the ids whose Promise.allSettled result was fulfilled. */
export function fulfilledIds<T>(ids: number[], results: PromiseSettledResult<T>[]): number[] {
    return ids.filter((_, index) => results[index].status === "fulfilled")
}
