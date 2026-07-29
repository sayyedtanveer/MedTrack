import { ActivityItem } from "@/types/inventory.types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatDistanceToNow } from "date-fns"
import { AlertCircle, ArrowRightLeft, Settings } from "lucide-react"

interface ActivityFeedProps {
  activities: ActivityItem[]
}

const getIcon = (type: string) => {
  switch (type) {
    case "movement": return <ArrowRightLeft className="h-4 w-4 text-primary" />
    case "alert": return <AlertCircle className="h-4 w-4 text-destructive" />
    case "system": return <Settings className="h-4 w-4 text-muted-foreground" />
    default: return <Settings className="h-4 w-4" />
  }
}

export function ActivityFeed({ activities }: ActivityFeedProps) {
  return (
    <Card className="col-span-1 border flex flex-col h-full shadow-sm">
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        <div className="space-y-8 h-full max-h-[350px] overflow-y-auto pr-3 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-slate-200/80 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-slate-300 transition-colors">
          {activities.length === 0 ? (
            <p className="text-sm text-muted-foreground">No recent activity.</p>
          ) : (
            activities.map((activity) => (
              <div key={activity.id} className="flex items-center">
                <div className="space-y-1">
                  <p className="text-sm font-medium leading-none flex items-center gap-2">
                    {getIcon(activity.type)}
                    {activity.description}
                  </p>
                  <p className="text-xs text-muted-foreground pl-6">
                    {activity.user && `${activity.user} • `} 
                    {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
