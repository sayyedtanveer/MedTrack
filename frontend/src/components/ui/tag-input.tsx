import { useState, KeyboardEvent } from "react"
import { Badge } from "@/components/ui/badge"
import { X } from "lucide-react"

export interface TagInputProps {
  value: string[]
  onChange: (value: string[]) => void
  placeholder?: string
  disabled?: boolean
}

export function TagInput({ value, onChange, placeholder, disabled }: TagInputProps) {
  const [inputValue, setInputValue] = useState("")

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return
    
    // Add tag on Enter or Comma
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      const val = inputValue.trim()
      if (val && !value.includes(val)) {
        onChange([...value, val])
      }
      setInputValue("")
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
    <div 
      className={`flex flex-wrap items-center gap-2 p-1.5 min-h-10 rounded-md border border-input bg-background text-sm ring-offset-background focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {value.map((tag) => (
        <Badge key={tag} variant="secondary" className="flex items-center gap-1 font-normal py-0.5 px-2">
          {tag}
          {!disabled && (
            <button
              type="button"
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
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={value.length === 0 ? placeholder : ""}
        disabled={disabled}
        className="flex-1 bg-transparent min-w-[120px] outline-none text-sm placeholder:text-muted-foreground px-1 py-0.5"
      />
    </div>
  )
}
