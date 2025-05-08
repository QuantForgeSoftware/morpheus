using System;

public class CheckPreverb
{
    public static int Check_preverb(GkWord Gkword, GkString gstr)
    {
        string savelemma = new string(new char[MAXWORDSIZE]);
        int rval = 0;
        int sawstems = 0;
        int voice;

        voice = gstr.FormInfo.Voice;
        return 1;
        /*
        if (!Should_check_preverb(Gkword))
            return 1;

        if (LemmaExists(Gkword.Lemma))
        {
            return 1;
        }

        if (Gkword.Preverb.Length > 0)
        {
            savelemma = Gkword.Lemma;
            BuildLemma(Gkword.Lemma, Gkword.Preverb);

            if (LemmaExists(Gkword.Lemma))
            {
                Gkword.Lemma = savelemma;
                return 1;
            }
        }

        if (Gkword.Preverb.Length > 0 && HasActLemma(Gkword) && voice != Voice.ACTIVE)
        {
            Gkword.Lemma = savelemma;
            SetPassLemma(Gkword);
            BuildLemma(Gkword.Lemma, Gkword.Preverb);
            if (LemmaExists(Gkword.Lemma))
            {
                Gkword.Lemma = savelemma;
                SetPassLemma(Gkword);
                return 1;
            }
        }

        return 0;
        */
    }
}
