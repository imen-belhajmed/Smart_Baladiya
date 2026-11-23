from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Commercant, Emplacement, Permis

User = get_user_model()


class ListeEmplacementsTests(TestCase):
    def setUp(self):
        self.url = reverse('marches:list')
        self.user = User.objects.create_user(
            username='citoyen1', password='motdepasse123'
        )
        Emplacement.objects.create(
            numero='A1', zone='Centre-ville',
            activite='Fruits et légumes', statut=Emplacement.Statut.LIBRE,
        )
        Emplacement.objects.create(
            numero='B2', zone='Marché Nord',
            activite='Poissonnerie', statut=Emplacement.Statut.RESERVE,
        )

    def numeros(self, reponse):
        return [e.numero for e in reponse.context['emplacements']]

    def test_visiteur_anonyme_est_redirige_vers_la_connexion(self):
        reponse = self.client.get(self.url)
        self.assertRedirects(
            reponse,
            f"{reverse('accounts:login')}?next={self.url}",
            fetch_redirect_response=False,
        )

    def test_utilisateur_connecte_voit_tous_les_emplacements(self):
        self.client.login(username='citoyen1', password='motdepasse123')
        reponse = self.client.get(self.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertCountEqual(self.numeros(reponse), ['A1', 'B2'])

    def test_filtre_par_zone(self):
        self.client.login(username='citoyen1', password='motdepasse123')
        reponse = self.client.get(self.url, {'zone': 'Centre-ville'})
        self.assertEqual(self.numeros(reponse), ['A1'])

    def test_filtre_par_statut(self):
        self.client.login(username='citoyen1', password='motdepasse123')
        reponse = self.client.get(self.url, {'statut': 'reserve'})
        self.assertEqual(self.numeros(reponse), ['B2'])


class PermisModelTests(TestCase):
    def setUp(self):
        self.commercant = Commercant.objects.create(
            nom='Ben Ali', prenom='Sami', cin='12345678',
            activite='Fruits et légumes',
        )
        self.emplacement = Emplacement.objects.create(
            numero='A1', zone='Centre-ville', activite='Fruits et légumes',
        )
        self.aujourdhui = timezone.localdate()

    def creer_permis(self, debut, fin, statut=Permis.Statut.ACTIF):
        return Permis(
            commercant=self.commercant, emplacement=self.emplacement,
            date_debut=debut, date_fin=fin, statut=statut,
        )

    def test_date_fin_doit_etre_apres_date_debut(self):
        permis = self.creer_permis(self.aujourdhui, self.aujourdhui)
        with self.assertRaises(ValidationError):
            permis.clean()

    def test_chevauchement_sur_le_meme_emplacement_est_refuse(self):
        self.creer_permis(
            self.aujourdhui, self.aujourdhui + timedelta(days=30)
        ).save()
        second = self.creer_permis(
            self.aujourdhui + timedelta(days=10),
            self.aujourdhui + timedelta(days=40),
        )
        with self.assertRaises(ValidationError):
            second.clean()

    def test_permis_actif_dans_ses_dates_est_valide(self):
        permis = self.creer_permis(
            self.aujourdhui - timedelta(days=1),
            self.aujourdhui + timedelta(days=30),
        )
        self.assertTrue(permis.est_valide)

    def test_permis_annule_n_est_pas_valide(self):
        permis = self.creer_permis(
            self.aujourdhui - timedelta(days=1),
            self.aujourdhui + timedelta(days=30),
            statut=Permis.Statut.ANNULE,
        )
        self.assertFalse(permis.est_valide)