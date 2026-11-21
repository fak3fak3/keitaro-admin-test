import { useUnit } from 'effector-react'
import type { FormEvent } from 'react'
import { Link } from 'react-router'

import { OfferAutocomplete } from '@/components/OfferAutocomplete'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  $canSubmit,
  $created,
  $fieldErrors,
  $formError,
  $geo,
  $name,
  createCampaignMutation,
  formSubmitted,
  geoChanged,
  nameChanged,
  offerSearch,
} from '@/models/newCampaign'

export function NewCampaignForm() {
  const [name, geo, canSubmit, pending, created, fieldErrors, formError] = useUnit([
    $name,
    $geo,
    $canSubmit,
    createCampaignMutation.$pending,
    $created,
    $fieldErrors,
    $formError,
  ])
  const [onName, onGeo, onSubmit] = useUnit([nameChanged, geoChanged, formSubmitted])

  function submit(event: FormEvent) {
    event.preventDefault()
    onSubmit()
  }

  // overflow-visible: у Card по умолчанию overflow-hidden, он обрезает выпадающий список офферов
  return (
    <Card className="overflow-visible">
      <CardHeader>
        <CardTitle>New campaign</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="grid gap-4 md:grid-cols-3" onSubmit={submit} noValidate>
          <Field id="campaign-name" label="Название" error={fieldErrors.name}>
            <Input
              id="campaign-name"
              placeholder="test_mirolyubov_campaign1"
              value={name}
              aria-invalid={Boolean(fieldErrors.name) || undefined}
              onChange={(event) => onName(event.target.value)}
            />
          </Field>
          <Field id="campaign-geo" label="Гео" error={fieldErrors.geo}>
            <Input
              id="campaign-geo"
              placeholder="MX,AU,RO"
              value={geo}
              aria-invalid={Boolean(fieldErrors.geo) || undefined}
              onChange={(event) => onGeo(event.target.value)}
            />
          </Field>
          <Field label="Оффер" error={fieldErrors.offer_id}>
            <OfferAutocomplete search={offerSearch} label="Оффер" invalid={Boolean(fieldErrors.offer_id)} />
          </Field>
          <div className="md:col-span-3">
            <Button type="submit" disabled={!canSubmit}>
              {pending ? 'Создаём…' : 'Создать кампанию'}
            </Button>
          </div>
        </form>

        {formError && (
          <Alert variant="destructive">
            <AlertDescription>{formError}</AlertDescription>
          </Alert>
        )}
        {created && (
          <Alert>
            <AlertDescription className="space-y-1">
              <p>Кампания {created.name} создана.</p>
              <p>
                <a className="underline" href={created.url} target="_blank" rel="noreferrer">
                  {created.url}
                </a>
                {' · '}
                <Link className="underline" to={`/campaigns/${created.keitaro_id}`}>
                  Открыть редактор
                </Link>
              </p>
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}

function Field({
  id,
  label,
  error,
  children,
}: {
  id?: string
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      {id ? <Label htmlFor={id}>{label}</Label> : <Label>{label}</Label>}
      {children}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}
