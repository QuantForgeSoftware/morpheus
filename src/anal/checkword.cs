using System;

public class CheckWord
{
    public static int checkword(GkWord Gkword)
    {
        int rval = 0;

        if (!Gkword.HasMorphflag(MorphFlags.UNAUGMENTED))
            rval += CheckIndecl(Gkword);

        if (rval > 0 && Gkword.QuickFlag)
            return rval;

        if (!Gkword.HasMorphflag(MorphFlags.UNAUGMENTED))
            rval += CheckNom(Gkword);

        if (rval > 0 && Gkword.QuickFlag)
            return rval;

        rval += CheckVerb(Gkword);

        return rval;
    }

    private static int CheckIndecl(GkWord Gkword)
    {
        // Placeholder for the actual implementation of CheckIndecl
        return 0;
    }

    private static int CheckNom(GkWord Gkword)
    {
        // Placeholder for the actual implementation of CheckNom
        return 0;
    }

    private static int CheckVerb(GkWord Gkword)
    {
        // Placeholder for the actual implementation of CheckVerb
        return 0;
    }
}

public class GkWord
{
    public bool QuickFlag { get; set; }

    public bool HasMorphflag(MorphFlags morphFlags)
    {
        // Placeholder for the actual implementation of HasMorphflag
        return false;
    }
}

public enum MorphFlags
{
    UNAUGMENTED = 1
}
