import { useUnit } from 'effector-react'
import { useEffect } from 'react'
import { Link } from 'react-router'

import { Alert, AlertDescription } from '@/components/ui/alert'
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
  campaignsPageOpened,
} from '@/models/campaigns'

import { NewCampaignForm } from './NewCampaignForm'

export function CampaignsPage() {
  const [campaigns, error, pending, opened] = useUnit([
    $campaigns,
    $campaignsError,
    $campaignsPending,
    campaignsPageOpened,
  ])

  useEffect(() => {
    opened()
  }, [opened])

  return (
    <section className="space-y-6">
      <NewCampaignForm />

      <h1 className="text-2xl font-semibold">Кампании</h1>

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
              <TableCell>{campaign.geo.join(', ')}</TableCell>
              <TableCell>{campaign.offer_id}</TableCell>
              <TableCell>
                <a className="text-muted-foreground hover:underline" href={campaign.url} target="_blank" rel="noreferrer">
                  {campaign.url}
                </a>
              </TableCell>
            </TableRow>
          ))}
          {!pending && campaigns.length === 0 && (
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
