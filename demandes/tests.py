import hashlib
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from . import services
from .models import DemandeAdministrative, Notification

User = get_user_model()
PDF = b"%PDF-1.4 document officiel"


class DemandesTests(TestCase):
    def setUp(self):
        self.citoyen = User.objects.create_user('citoyen', password='x', role='citoyen')
        self.autre = User.objects.create_user('autre', password='x', role='citoyen')
        self.agent = User.objects.create_user('agent', password='x', role='agent')

    def demande(self, **kw):
        kw.setdefault('type_document', 'residence')
        return DemandeAdministrative.objects.create(citoyen=self.citoyen, **kw)

    # ---------- CRUD citoyen
    def test_creation_estime_delai_et_notifie(self):
        self.client.force_login(self.citoyen)
        r = self.client.post(reverse('demandes:creer'), {'type_document': 'extrait_naissance', 'motif': 'x'})
        d = DemandeAdministrative.objects.get()
        self.assertRedirects(r, reverse('demandes:detail', args=[d.pk]))
        self.assertGreaterEqual(d.delai_estime_heures, 1)
        self.assertIsNotNone(d.date_prevue)
        self.assertTrue(Notification.objects.filter(destinataire=self.citoyen).exists())
        self.assertTrue(Notification.objects.filter(destinataire=self.agent).exists())

    def test_citoyen_ne_voit_que_ses_demandes(self):
        mine = self.demande(motif='la mienne')
        DemandeAdministrative.objects.create(citoyen=self.autre, type_document='autre', motif='autre')
        self.client.force_login(self.citoyen)
        r = self.client.get(reverse('demandes:liste'))
        self.assertEqual(list(r.context['demandes']), [mine])
        other = DemandeAdministrative.objects.get(citoyen=self.autre)
        self.assertEqual(self.client.get(reverse('demandes:detail', args=[other.pk])).status_code, 403)

    def test_modifier_et_annuler_seulement_en_attente(self):
        d = self.demande()
        self.client.force_login(self.citoyen)
        self.assertEqual(self.client.get(reverse('demandes:modifier', args=[d.pk])).status_code, 200)
        self.client.post(reverse('demandes:annuler', args=[d.pk]))
        d.refresh_from_db()
        self.assertEqual(d.statut, 'annulee')
        d2 = self.demande(statut='validee')
        self.client.post(reverse('demandes:annuler', args=[d2.pk]))
        d2.refresh_from_db()
        self.assertEqual(d2.statut, 'validee')
        self.assertRedirects(self.client.get(reverse('demandes:modifier', args=[d2.pk])), reverse('demandes:liste'))

    # ---------- Agent
    def test_espace_agent_reserve(self):
        d = self.demande()
        self.client.force_login(self.citoyen)
        self.assertEqual(self.client.get(reverse('demandes:tableau_agent')).status_code, 403)
        self.assertEqual(self.client.get(reverse('demandes:traiter_demande', args=[d.pk])).status_code, 403)
        self.client.force_login(self.agent)
        self.assertEqual(self.client.get(reverse('demandes:tableau_agent')).status_code, 200)

    def test_validation_exige_un_document(self):
        d = self.demande()
        self.client.force_login(self.agent)
        r = self.client.post(reverse('demandes:traiter_demande', args=[d.pk]), {'statut': 'validee'})
        self.assertEqual(r.status_code, 200)
        d.refresh_from_db()
        self.assertEqual(d.statut, 'en_attente')

    def valider(self, d):
        self.client.force_login(self.agent)
        self.client.post(reverse('demandes:traiter_demande', args=[d.pk]), {
            'statut': 'validee', 'commentaire_agent': 'ok',
            'document_delivre': SimpleUploadedFile('acte.pdf', PDF)})
        d.refresh_from_db()

    def test_validation_empreinte_notification_telechargement(self):
        d = self.demande()
        avant = Notification.objects.filter(destinataire=self.citoyen).count()
        self.valider(d)
        self.assertEqual(d.statut, 'validee')
        self.assertEqual(d.empreinte_document, hashlib.sha256(PDF).hexdigest())
        self.assertEqual(d.agent_traitant, self.agent)
        self.assertEqual(Notification.objects.filter(destinataire=self.citoyen).count(), avant + 1)
        self.client.force_login(self.citoyen)
        self.assertEqual(self.client.get(reverse('demandes:telecharger', args=[d.pk])).status_code, 200)
        self.client.force_login(self.autre)
        self.assertEqual(self.client.get(reverse('demandes:telecharger', args=[d.pk])).status_code, 403)

    def test_suppression_par_agent(self):
        d = self.demande()
        self.client.force_login(self.agent)
        self.client.post(reverse('demandes:supprimer', args=[d.pk]))
        self.assertFalse(DemandeAdministrative.objects.filter(pk=d.pk).exists())

    # ---------- Vérification d'authenticité (publique)
    def test_verification_authenticite(self):
        d = self.demande()
        self.valider(d)
        self.client.logout()
        url = reverse('demandes:verifier')
        r = self.client.post(url, {'code': d.empreinte_verification, 'document': SimpleUploadedFile('a.pdf', PDF)})
        self.assertEqual(r.context['resultat'], 'authentique')
        r = self.client.post(url, {'code': d.empreinte_verification, 'document': SimpleUploadedFile('a.pdf', PDF + b'x')})
        self.assertEqual(r.context['resultat'], 'modifie')
        r = self.client.post(url, {'code': '00000000-0000-0000-0000-000000000000'})
        self.assertEqual(r.context['resultat'], 'inconnu')
        r = self.client.get(url, {'code': d.empreinte_verification})
        self.assertEqual(r.context['resultat'], 'trouve')
        self.assertNotContains(r, self.citoyen.username)  # nom masqué

    # ---------- Délais intelligents & retards
    def test_delai_appris_de_l_historique_et_de_la_charge(self):
        base = services.estimer_delai_heures('legalisation')
        for _ in range(4):
            x = self.demande(type_document='legalisation', statut='validee')
            DemandeAdministrative.objects.filter(pk=x.pk).update(date_creation=timezone.now() - timedelta(hours=11))
        self.assertGreater(services.estimer_delai_heures('legalisation'), base)
        for _ in range(12):
            self.demande(type_document='autre')
        self.assertGreater(services.estimer_delai_heures('autre'), services.DELAIS_BASE_HEURES['autre'])

    def test_retard_notifie_une_seule_fois(self):
        d = self.demande()
        DemandeAdministrative.objects.filter(pk=d.pk).update(date_prevue=timezone.now() - timedelta(hours=1))
        self.assertEqual(services.notifier_retards(), 1)
        self.assertEqual(services.notifier_retards(), 0)
        self.assertTrue(Notification.objects.filter(destinataire=self.citoyen, message__startswith='Retard').exists())
        self.client.force_login(self.citoyen)
        self.assertContains(self.client.get(reverse('demandes:detail', args=[d.pk])), 'dépasse le délai')

    def test_notifications_marquees_lues(self):
        self.demande()
        self.client.force_login(self.citoyen)
        self.assertTrue(self.client.get(reverse('home')).context['nb_notifs_demandes'] > 0)
        self.client.get(reverse('demandes:notifications'))
        self.assertEqual(self.citoyen.notifications_demandes.filter(lue=False).count(), 0)
