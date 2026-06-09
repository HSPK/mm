import { useCallback, useEffect, useState } from "react"
import { libraryRepo, type LibraryInfo } from "@/api/library"

export interface UseImportTemplateResult {
    template: string
    setTemplate: (value: string) => void
    saving: boolean
    saved: boolean
    save: () => Promise<void>
}

/**
 * Loads + persists the library's `import_template` config string. Refetches
 * whenever the `currentLibrary` (passed in) changes so switching libraries
 * pulls the right template.
 */
export function useImportTemplate(currentLibrary: LibraryInfo | null): UseImportTemplateResult {
    const [template, setTemplate] = useState("")
    const [saving, setSaving] = useState(false)
    const [saved, setSaved] = useState(false)

    useEffect(() => {
        libraryRepo.getConfig()
            .then((cfg) => {
                if (cfg.import_template) setTemplate(cfg.import_template)
            })
            .catch(() => { })
    }, [currentLibrary])

    const save = useCallback(async () => {
        setSaving(true)
        setSaved(false)
        try {
            await libraryRepo.updateConfig({ import_template: template })
            setSaved(true)
            setTimeout(() => setSaved(false), 2000)
        } catch {
            // intentionally swallow — UI shows the unchanged "Save" button
        } finally {
            setSaving(false)
        }
    }, [template])

    return { template, setTemplate, saving, saved, save }
}

const SAMPLE_VARIABLES: Array<[string, string]> = [
    ["{year}", "2024"],
    ["{month:02d}", "03"],
    ["{month}", "3"],
    ["{day:02d}", "15"],
    ["{day}", "15"],
    ["{camera}", "Sony A7IV"],
    ["{type}", "photo"],
    ["{ext}", ".jpg"],
    ["{original_name}", "DSC_0001"],
]

/** Pure preview formatter; extract here so it's easy to add new variables. */
export function previewImportTemplate(template: string): string {
    return SAMPLE_VARIABLES.reduce(
        (acc, [token, value]) => acc.replaceAll(token, value),
        template,
    )
}
