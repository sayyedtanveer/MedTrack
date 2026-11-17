import { useState, type KeyboardEvent } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { X } from "lucide-react"

export interface TagInputProps {
  value: string[]
  onChange: (value: string[]) => void
  placeholder?: string
  disabled?: boolean
  label?: string
}

export function TagInput({ value, onChange, placeholder, disabled, label = "Option" }: TagInputProps) {
  const [inputValue, setInputValue] = useState("")

  const [error, setError] = useState("")

  const addTag = () => {
    const option = inputValue.trim()
    if (!option || disabled) return
    if (value.some((tag) => tag.trim().toLowerCase() === option.toLowerCase())) {
      setError("This option already exists.")
      return
    }
    onChange([...value, option])
    setInputValue("")
    setError("")
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (disabled || e.nativeEvent.isComposing) return
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      addTag()
    }

    // Remove last tag on Backspace if input is empty
    if (e.key === "Backspace" && inputValue === "" && value.length > 0) {
      e.preventDefault()
      onChange(value.slice(0, -1))
    }
  }

  const removeTag = (tagToRemove: string) => {
    if (disabled) return
    onChange(value.filter(tag => tag !== tagToRemove))
  }

  return (
    <div className="space-y-1">
      <div
        className={`flex flex-wrap items-center gap-2 p-1.5 min-h-10 rounded-md border border-input bg-background text-sm ring-offset-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {value.map((tag) => (
          <Badge key={tag} variant="secondary" className="flex items-center gap-1 font-normal py-0.5 px-2">
            {tag}
            {!disabled && (
              <button
                type="button"
                aria-label={`Remove ${tag}`}
                onClick={() => removeTag(tag)}
                className="ml-1 ring-offset-background rounded-full outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 hover:bg-muted"
              >
                <X className="w-3 h-3 text-muted-foreground hover:text-foreground" />
              </button>
            )}
          </Badge>
        ))}
        <input
          type="text"
          value={inputValue}
          aria-label={label}
          aria-invalid={Boolean(error)}
          onChange={(e) => {
            setInputValue(e.target.value)
            setError("")
          }}
          onKeyDown={handleKeyDown}
          placeholder={value.length === 0 ? placeholder : ""}
          disabled={disabled}
          className="flex-1 bg-transparent min-w-[120px] outline-none text-sm placeholder:text-muted-foreground px-1 py-0.5"
        />
        {!disabled && <Button type="button" size="sm" variant="outline" onClick={addTag} disabled={!inputValue.trim()}>Add</Button>}
      </div>
      {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
    </div>
  )
}
