import { describe, expect, it } from "vitest"
import { seekAudio } from "./music-player-transport"

describe("music player transport", () => {
    it("updates and clamps the HTML audio position", () => {
        const audio = { currentTime: 40, duration: 120 }

        expect(seekAudio(audio, 0)).toBe(0)
        expect(audio.currentTime).toBe(0)
        expect(seekAudio(audio, 200)).toBe(120)
        expect(audio.currentTime).toBe(120)
    })
})
