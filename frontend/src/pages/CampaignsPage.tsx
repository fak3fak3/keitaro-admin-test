import { useUnit } from 'effector-react'
import { Loader2, Plus } from 'lucide-react'
import { type FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  $campaigns,
  $campaignsError,
  $campaignsPending,
  $canConnect,
  $connectError,
  $connectId,
  connectCampaignMutation,
  connectIdChanged,
  connectSubmitted,
  campaignsPageOpened,
} from '@/models/campaigns'

import { NewCampaignForm } from './NewCampaignForm'

export function CampaignsPage() {
  const [campaigns, error, pending, opened, connectId, canConnect, connectError, connecting] = useUnit([
    $campaigns,
    $campaignsError,
    $campaignsPending,
    campaignsPageOpened,
    $connectId,
    $canConnect,
    $connectError,
    connectCampaignMutation.$pending,
  ])
  const [onConnectId, onConnect] = useUnit([connectIdChanged, connectSubmitted])
  const [formOpen, setFormOpen] = useState(false)

  useEffect(() => {
    opened()
  }, [opened])

  function submitConnect(event: FormEvent) {
    event.preventDefault()
    onConnect()
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Кампании</h1>
        {!formOpen && (
          <Button onClick={() => setFormOpen(true)}>
            <Plus aria-hidden />
            New campaign
          </Button>
        )}
      </div>

      {formOpen && <NewCampaignForm onClose={() => setFormOpen(false)} />}

      <form className="flex flex-wrap items-end gap-3" onSubmit={submitConnect}>
        <div className="grid gap-2">
          <Label htmlFor="keitaro-campaign-id">ID кампании Keitaro</Label>
          <Input
            id="keitaro-campaign-id"
            inputMode="numeric"
            value={connectId}
            onChange={(event) => onConnectId(event.target.value)}
            placeholder="Например, 217109"
          />
          <p className="text-sm text-muted-foreground">
            Кампания появится в списке. Потоки загрузите на странице редактора.
          </p>
        </div>
        <Button type="submit" disabled={!canConnect}>
          {connecting ? 'Подключаем…' : 'Подключить'}
        </Button>
      </form>

      {connectError && (
        <Alert variant="destructive">
          <AlertDescription>{connectError}</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Название</TableHead>
            <TableHead>Гео</TableHead>
            <TableHead>Оффер</TableHead>
            <TableHead>Ссылка</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {campaigns.map((campaign) => (
            <TableRow key={campaign.keitaro_id}>
              <TableCell>
                <Link className="font-medium underline-offset-4 hover:underline" to={`/campaigns/${campaign.keitaro_id}`}>
                  {campaign.name}
                </Link>
              </TableCell>
              <TableCell>{campaign.geo?.join(', ') || '—'}</TableCell>
              <TableCell>{campaign.offer_id ?? '—'}</TableCell>
              <TableCell>
                <a className="text-muted-foreground hover:underline" href={campaign.url} target="_blank" rel="noreferrer">
                  {campaign.url}
                </a>
              </TableCell>
            </TableRow>
          ))}
          {pending && campaigns.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-muted-foreground">
                <span className="flex items-center gap-2">
                  <Loader2 aria-hidden className="size-4 animate-spin" />
                  Загружаем кампании…
                </span>
              </TableCell>
            </TableRow>
          )}
          {!pending && !error && campaigns.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-muted-foreground">
                Кампаний пока нет
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </section>
  )
}
