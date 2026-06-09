import type { MetadataForm } from "@/hooks/use-media-edit-form"

function toDateTimeLocalValue(value: unknown) {
    return value ? String(value).replace(/Z$/, "").slice(0, 16) : ""
}

const inputClass = "w-full bg-white/[0.04] border border-white/[0.08] rounded-lg text-white text-xs px-2.5 py-2 focus:outline-none focus:border-white/20 transition-colors"
const legendClass = "text-[10px] uppercase tracking-wider text-white/30 font-semibold"
const labelClass = "text-[9px] uppercase tracking-wider text-white/20 font-medium block pl-0.5"

interface FieldSpec {
    key: keyof MetadataForm
    label: string
    type?: "text" | "number"
    step?: string
    placeholder?: string
    parse?: (raw: string) => unknown
}

function Field({
    spec,
    form,
    onChange,
}: {
    spec: FieldSpec
    form: MetadataForm
    onChange: (key: string, value: unknown) => void
}) {
    const value = form[spec.key] as unknown
    return (
        <div className="space-y-1">
            <label className={labelClass}>{spec.label}</label>
            <input
                type={spec.type ?? "text"}
                step={spec.step}
                className={inputClass}
                value={(value as string | number | undefined) ?? ""}
                onChange={(e) => onChange(spec.key as string, spec.parse ? spec.parse(e.target.value) : e.target.value)}
                placeholder={spec.placeholder}
            />
        </div>
    )
}

const locationFields: FieldSpec[] = [
    { key: "gps_lat", label: "Latitude", type: "number", step: "any", placeholder: "30.0000", parse: (v) => v ? parseFloat(v) : null },
    { key: "gps_lon", label: "Longitude", type: "number", step: "any", placeholder: "120.0000", parse: (v) => v ? parseFloat(v) : null },
]
const placeFields: FieldSpec[] = [
    { key: "location_label", label: "Place Name", placeholder: "e.g. Times Square" },
]
const localityFields: FieldSpec[] = [
    { key: "location_city", label: "City", placeholder: "City" },
    { key: "location_country", label: "Country", placeholder: "Country" },
]
const deviceFields: FieldSpec[] = [
    { key: "camera_make", label: "Make", placeholder: "e.g. Sony" },
    { key: "camera_model", label: "Model", placeholder: "e.g. A7R V" },
]
const lensFields: FieldSpec[] = [
    { key: "lens_model", label: "Lens", placeholder: "e.g. FE 24-70mm F2.8 GM II" },
]
const exposureFields: FieldSpec[] = [
    { key: "focal_length", label: "Focal Length", type: "number", placeholder: "mm", parse: (v) => v ? parseFloat(v) : null },
    { key: "aperture", label: "Aperture", type: "number", step: "any", placeholder: "f/", parse: (v) => v ? parseFloat(v) : null },
    { key: "iso", label: "ISO", type: "number", placeholder: "e.g. 100", parse: (v) => v ? parseInt(v) : null },
    { key: "shutter_speed", label: "Shutter Speed", placeholder: "e.g. 1/250" },
]

interface MetadataEditorProps {
    form: MetadataForm
    onChange: (key: string, value: unknown) => void
}

export function MetadataEditor({ form, onChange }: MetadataEditorProps) {
    return (
        <div className="py-4 space-y-5">
            <fieldset className="space-y-1.5">
                <legend className={legendClass}>Date Taken</legend>
                <input
                    type="datetime-local"
                    className={inputClass}
                    value={toDateTimeLocalValue(form.date_taken)}
                    onChange={(e) => onChange("date_taken", e.target.value || null)}
                />
            </fieldset>

            <Divider />

            <fieldset className="space-y-2.5">
                <legend className={legendClass}>Location</legend>
                <FieldGrid fields={locationFields} form={form} onChange={onChange} />
                {placeFields.map((spec) => (
                    <Field key={spec.key} spec={spec} form={form} onChange={onChange} />
                ))}
                <FieldGrid fields={localityFields} form={form} onChange={onChange} />
            </fieldset>

            <Divider />

            <fieldset className="space-y-2.5">
                <legend className={legendClass}>Device</legend>
                <FieldGrid fields={deviceFields} form={form} onChange={onChange} />
                {lensFields.map((spec) => (
                    <Field key={spec.key} spec={spec} form={form} onChange={onChange} />
                ))}
            </fieldset>

            <Divider />

            <fieldset className="space-y-2.5">
                <legend className={legendClass}>Exposure</legend>
                <FieldGrid fields={exposureFields} form={form} onChange={onChange} />
            </fieldset>
        </div>
    )
}

function FieldGrid({
    fields,
    form,
    onChange,
}: {
    fields: FieldSpec[]
    form: MetadataForm
    onChange: (key: string, value: unknown) => void
}) {
    return (
        <div className="grid grid-cols-2 gap-2">
            {fields.map((spec) => (
                <Field key={spec.key} spec={spec} form={form} onChange={onChange} />
            ))}
        </div>
    )
}

function Divider() {
    return <div className="h-px bg-white/[0.05]" />
}
